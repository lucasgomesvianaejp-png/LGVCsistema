from __future__ import annotations

import csv
import io
from typing import Any

from .common import IngestionRun, SupabaseRest, http_bytes, parse_date, parse_decimal, sha256

TESOURO_CSV = 'https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv'


def _pick(row: dict[str, Any], *names: str) -> Any:
    normalized = {str(k).strip().lower(): v for k,v in row.items()}
    for name in names:
        if name.lower() in normalized:
            return normalized[name.lower()]
    return None


def _rate(value):
    number = parse_decimal(value)
    if number is None: return None
    return number / 100.0 if abs(number) > 1 else number


def ingest_tesouro(db: SupabaseRest) -> None:
    run = IngestionRun(db, 'TESOURO_TD', source_url=TESOURO_CSV)
    try:
        payload = http_bytes(TESOURO_CSV, timeout=180)
        digest = sha256(payload)
        text = payload.decode('utf-8-sig', errors='replace')
        sample = text[:5000]
        delimiter = ';' if sample.count(';') > sample.count(',') else ','
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        rows = []
        for raw in reader:
            run.rows_read += 1
            title = _pick(raw, 'Tipo Titulo', 'Tipo Título', 'TipoTitulo')
            base_date = parse_date(_pick(raw, 'Data Base', 'DataBase'))
            maturity = parse_date(_pick(raw, 'Data Vencimento', 'DataVencimento'))
            if not title or not base_date or not maturity:
                continue
            rows.append({
                'rate_date': base_date, 'title_type': str(title).strip(), 'maturity_date': maturity,
                'buy_rate': _rate(_pick(raw, 'Taxa Compra Manha', 'Taxa Compra Manhã', 'TaxaCompraManha')),
                'sell_rate': _rate(_pick(raw, 'Taxa Venda Manha', 'Taxa Venda Manhã', 'TaxaVendaManha')),
                'buy_price': parse_decimal(_pick(raw, 'PU Compra Manha', 'PU Compra Manhã', 'PUCompraManha')),
                'sell_price': parse_decimal(_pick(raw, 'PU Venda Manha', 'PU Venda Manhã', 'PUVendaManha')),
                'source': 'TESOURO_TD', 'source_grade': 'A', 'source_url': TESOURO_CSV,
            })
        run.rows_written = db.upsert('lgv_treasury_rates', rows, 'rate_date,title_type,maturity_date', batch_size=1000)
        run.success(digest, {'records': len(rows)})
    except Exception as exc:
        run.fail(exc)
        raise
