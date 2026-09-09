from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import date
from typing import Any

from .common import IngestionRun, SupabaseRest, b64_params, date_after, http_bytes, http_json, parse_date, parse_decimal, sha256

COTAHIST_URL = 'https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP'
B3_PROXY = 'https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall'


def _num(line: str, start: int, end: int, decimals: int = 0) -> float:
    raw = line[start - 1:end].strip() or '0'
    value = int(raw)
    return value / (10 ** decimals)


def _txt(line: str, start: int, end: int) -> str:
    return line[start - 1:end].strip()


def is_equity_spec(spec: str, isin: str) -> bool:
    s = (spec or '').upper().strip()
    # Ações/units. Exclui recibos/direitos/fundos/BDRs pelo padrão da especificação/ISIN.
    if 'BDR' in s or 'DRN' in s or 'DR1' in s or 'CI' == s:
        return False
    return bool(re.search(r'(^|\s)(ON|PN|PNA|PNB|PNC|PND|UNT)(\s|$)', s)) and str(isin).startswith('BR')


def parse_cotahist_line(line: str) -> dict[str, Any] | None:
    if len(line) < 245 or line[:2] != '01':
        return None
    market_type = int(_txt(line, 25, 27) or 0)
    if market_type != 10:  # mercado à vista padrão; fracionário não é série econômica separada
        return None
    ticker = _txt(line, 13, 24).upper()
    spec = _txt(line, 40, 49)
    isin = _txt(line, 231, 242)
    if not ticker or not is_equity_spec(spec, isin):
        return None
    factor = int(_txt(line, 211, 217) or 1) or 1
    div = 100.0 * factor
    return {
        'ticker': ticker,
        'price_date': parse_date(_txt(line, 3, 10)),
        'bdi_code': _txt(line, 11, 12),
        'company_name': _txt(line, 28, 39),
        'share_class': spec,
        'open': _num(line, 57, 69, 2) / factor,
        'high': _num(line, 70, 82, 2) / factor,
        'low': _num(line, 83, 95, 2) / factor,
        'average': _num(line, 96, 108, 2) / factor,
        'close': _num(line, 109, 121, 2) / factor,
        'trades': int(_txt(line, 148, 152) or 0),
        'quantity': int(_txt(line, 153, 170) or 0),
        'financial_volume': _num(line, 171, 188, 2),
        'quote_factor': factor,
        'market_type': market_type,
        'isin': isin,
        'issuing_company_guess': ticker[:4],
    }


def _catalog_results(body: Any) -> list[dict[str, Any]]:
    if isinstance(body, dict):
        for key in ('results', 'companies', 'data'):
            value = body.get(key)
            if isinstance(value, list):
                return value
    return body if isinstance(body, list) else []


def fetch_company_catalog() -> list[dict[str, Any]]:
    companies: list[dict[str, Any]] = []
    page = 1
    while True:
        params = {'language': 'pt-br', 'pageNumber': page, 'pageSize': 120}
        body = http_json(f'{B3_PROXY}/GetInitialCompanies/{b64_params(params)}')
        rows = _catalog_results(body)
        if not rows:
            break
        companies.extend(rows)
        total_pages = None
        if isinstance(body, dict):
            page_info = body.get('page') or body.get('pagination') or {}
            total_pages = page_info.get('totalPages') or body.get('totalPages')
        if total_pages and page >= int(total_pages):
            break
        if len(rows) < 120:
            break
        page += 1
        if page > 100:
            break
    return companies


def ingest_company_catalog(db: SupabaseRest) -> dict[str, dict[str, Any]]:
    run = IngestionRun(db, 'B3_LISTED_CATALOG', source_url=f'{B3_PROXY}/GetInitialCompanies')
    try:
        raw = fetch_company_catalog()
        run.rows_read = len(raw)
        rows = []
        for item in raw:
            code = item.get('codeCVM') or item.get('codeCvm')
            try: code = int(code) if code not in (None, '') else None
            except (TypeError, ValueError): code = None
            issuing = str(item.get('issuingCompany') or item.get('code') or '').strip().upper() or None
            if not code and not issuing:
                continue
            rows.append({
                'code_cvm': code,
                'issuing_company': issuing,
                'trading_name': item.get('tradingName'),
                'company_name': item.get('companyName') or item.get('company'),
                'cnpj': item.get('cnpj'),
                'b3_company_id': str(item.get('id') or item.get('companyId') or '') or None,
                'source': 'B3_LISTED', 'source_grade': 'A',
            })
        # O conflito principal é code_cvm. Registros sem code_cvm serão completados pelo COTAHIST mais tarde.
        with_code = [r for r in rows if r['code_cvm'] is not None]
        run.rows_written = db.upsert('lgv_issuers', with_code, 'code_cvm') if with_code else 0
        run.success()
        return {str(r['issuing_company']): r for r in db.select('lgv_issuers', 'select=id,code_cvm,issuing_company,trading_name,company_name&issuing_company=not.is.null')}
    except Exception as exc:
        run.fail(exc)
        raise


def ingest_cotahist_year(db: SupabaseRest, year: int) -> None:
    url = COTAHIST_URL.format(year=year)
    run = IngestionRun(db, 'B3_COTAHIST', source_url=url, run_key=str(year), metadata={'year': year})
    try:
        payload = http_bytes(url, timeout=180)
        digest = sha256(payload)
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            txt_names = [n for n in zf.namelist() if n.upper().endswith('.TXT')]
            if not txt_names:
                raise RuntimeError('ZIP COTAHIST sem TXT')
            content = zf.read(txt_names[0]).decode('latin-1', errors='replace').splitlines()

        records = []
        asset_meta: dict[str, dict[str, Any]] = {}
        for line in content:
            rec = parse_cotahist_line(line)
            if not rec or not rec['price_date']:
                continue
            run.rows_read += 1
            asset_meta[rec['ticker']] = rec
            records.append(rec)

        issuers = db.select('lgv_issuers', 'select=id,issuing_company,code_cvm&issuing_company=not.is.null')
        issuer_map = {str(x['issuing_company']).upper(): x for x in issuers}
        asset_rows = []
        for ticker, rec in asset_meta.items():
            issuer = issuer_map.get(rec['issuing_company_guess'])
            asset_rows.append({
                'ticker': ticker,
                'company_name': rec['company_name'] or ticker,
                'issuer_id': issuer.get('id') if issuer else None,
                'code_cvm': issuer.get('code_cvm') if issuer else None,
                'asset_class': 'ACAO',
                'share_class': rec['share_class'], 'isin': rec['isin'],
                'bdi_code': rec['bdi_code'], 'quote_factor': rec['quote_factor'],
                'is_active': True,
            })
        run.rows_written += db.upsert('lgv_assets', asset_rows, 'ticker')

        assets = db.select('lgv_assets', 'select=id,ticker&asset_class=eq.ACAO')
        ids = {x['ticker']: x['id'] for x in assets}
        price_rows = []
        for rec in records:
            asset_id = ids.get(rec['ticker'])
            if not asset_id:
                continue
            price_rows.append({
                'asset_id': asset_id, 'price_date': rec['price_date'],
                'open': rec['open'], 'high': rec['high'], 'low': rec['low'],
                'average': rec['average'], 'close': rec['close'],
                'trades': rec['trades'], 'quantity': rec['quantity'],
                'financial_volume': rec['financial_volume'], 'isin': rec['isin'],
                'quote_factor': rec['quote_factor'], 'market_type': rec['market_type'],
                'source': 'B3_COTAHIST', 'source_grade': 'A', 'source_url': url,
            })
        run.rows_written += db.upsert('lgv_market_prices', price_rows, 'asset_id,price_date', batch_size=1000)
        run.success(digest, {'year': year, 'equity_rows': len(records), 'assets': len(asset_rows)})
    except Exception as exc:
        run.fail(exc)
        raise


def _result_list(body: Any, preferred: str) -> list[dict[str, Any]]:
    if isinstance(body, dict):
        value = body.get(preferred)
        if isinstance(value, list): return value
        for key in ('results','data'):
            value = body.get(key)
            if isinstance(value, list): return value
    return body if isinstance(body, list) else []


def fetch_company_supplement(issuing_company: str) -> dict[str, Any]:
    params = {'issuingCompany': issuing_company, 'language': 'pt-br'}
    body = http_json(f'{B3_PROXY}/GetListedSupplementCompany/{b64_params(params)}')
    return body if isinstance(body, dict) else {}


def ingest_company_supplements(db: SupabaseRest) -> None:
    """Uma chamada por emissor traz metadados, proventos em dinheiro e eventos em ações."""
    run = IngestionRun(db, 'B3_LISTED_SUPPLEMENT', source_url=f'{B3_PROXY}/GetListedSupplementCompany')
    try:
        issuers = db.select('lgv_issuers', 'select=id,code_cvm,issuing_company,trading_name&issuing_company=not.is.null')
        assets = db.select('lgv_assets', 'select=id,issuer_id,isin&asset_class=eq.ACAO&isin=not.is.null')
        tracked_issuer_ids = {a['issuer_id'] for a in assets if a.get('issuer_id')}
        isin_map = {str(a['isin']).strip().upper(): a['id'] for a in assets if a.get('isin')}
        cash_rows: list[dict[str, Any]] = []
        stock_rows: list[dict[str, Any]] = []
        issuer_updates: list[dict[str, Any]] = []
        checked = 0
        for issuer in issuers:
            if tracked_issuer_ids and issuer['id'] not in tracked_issuer_ids:
                continue
            body = fetch_company_supplement(str(issuer['issuing_company']))
            checked += 1
            info = body.get('info') if isinstance(body.get('info'), dict) else body
            issuer_updates.append({
                'id': issuer['id'],
                'code_cvm': issuer.get('code_cvm'),
                'issuing_company': issuer.get('issuing_company'),
                'trading_name': info.get('tradingName') or issuer.get('trading_name'),
                'segment': info.get('segment'),
                'round_lot': int(parse_decimal(info.get('roundLot')) or 0) or None,
                'common_shares': parse_decimal(info.get('numberCommonShares')),
                'preferred_shares': parse_decimal(info.get('numberPreferredShares')),
                'total_shares': parse_decimal(info.get('totalNumberShares')),
                'quoted_since': parse_date(info.get('quotedPerSharSince') or info.get('quotedSince')),
                'supplement_ref_date': parse_date(info.get('refdate')),
                'source': 'B3_LISTED', 'source_grade': 'A',
            })
            cash = body.get('cashDividends') or []
            stocks = body.get('stockDividends') or []
            run.rows_read += len(cash) + len(stocks)
            for e in cash:
                isin = str(e.get('isinCode') or e.get('assetIssued') or '').strip().upper()
                last_com = e.get('lastDatePrior')
                ex_date = parse_date(e.get('exDate')) or date_after(last_com)
                amount = parse_decimal(e.get('rate'))
                if not isin or not ex_date or amount is None:
                    continue
                cash_rows.append({
                    'issuer_id': issuer['id'], 'asset_id': isin_map.get(isin), 'isin': isin,
                    'declared_date': parse_date(e.get('approvedOn')), 'ex_date': ex_date,
                    'payment_date': parse_date(e.get('paymentDate')), 'event_type': str(e.get('label') or 'PROVENTO').upper(),
                    'amount_per_share': amount, 'reference_period': e.get('relatedTo'),
                    'observations': e.get('remarks'), 'recurrence_class': 'PENDING',
                    'source': 'B3_LISTED', 'source_grade': 'A',
                    'source_url': f'{B3_PROXY}/GetListedSupplementCompany',
                })
            for e in stocks:
                isin = str(e.get('isinCode') or '').strip().upper()
                event_date = parse_date(e.get('exDate')) or date_after(e.get('lastDatePrior')) or parse_date(e.get('approvedOn'))
                factor = parse_decimal(e.get('factor'))
                if not isin or not event_date or factor is None:
                    continue
                stock_rows.append({
                    'issuer_id': issuer['id'], 'asset_id': isin_map.get(isin), 'isin': isin,
                    'event_date': event_date, 'action_type': str(e.get('label') or 'CORPORATE_ACTION').upper(),
                    'factor': factor, 'emitted_isin': e.get('assetIssued'), 'observations': e.get('remarks'),
                    'source': 'B3_LISTED', 'source_grade': 'A',
                    'source_url': f'{B3_PROXY}/GetListedSupplementCompany',
                })
        # id é PK e permite atualizar o suplemento sem depender de código CVM ausente.
        run.rows_written += db.upsert('lgv_issuers', issuer_updates, 'id')
        run.rows_written += db.upsert('lgv_dividends', cash_rows, 'isin,ex_date,event_type,amount_per_share', batch_size=500)
        run.rows_written += db.upsert('lgv_corporate_actions', stock_rows, 'isin,event_date,action_type,factor', batch_size=500)
        run.success(metadata={'issuers_checked': checked, 'cash_events': len(cash_rows), 'stock_events': len(stock_rows)})
    except Exception as exc:
        run.fail(exc)
        raise


# Alias mantido para compatibilidade com o CLI v1.
def ingest_cash_dividends(db: SupabaseRest) -> None:
    ingest_company_supplements(db)

