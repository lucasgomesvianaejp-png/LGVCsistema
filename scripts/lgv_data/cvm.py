from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import PurePosixPath
from typing import Any

from .common import IngestionRun, SupabaseRest, http_bytes, parse_date, parse_decimal, sha256

CVM_URL = 'https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{doc}/DADOS/{doc_lower}_cia_aberta_{year}.zip'

# Apenas linhas necessárias ao motor LGV. Evita transformar o banco em réplica integral da CVM.
ACCOUNT_PREFIXES = {
    'DRE': ('3.01', '3.05', '3.11'),
    'BPA': ('1.01',),
    'BPP': ('2.01.04', '2.02.01', '2.03'),
    'DFC_MI': ('6.01', '6.02'),
    'DFC_MD': ('6.01', '6.02'),
}


def _statement_from_name(name: str) -> tuple[str, str] | None:
    upper = PurePosixPath(name).name.upper()
    for statement in ('DFC_MI','DFC_MD','DRE','BPA','BPP'):
        if f'_{statement}_CON_' in upper:
            return statement, 'CON'
        if f'_{statement}_IND_' in upper:
            return statement, 'IND'
    return None


def _interesting(statement: str, account_code: str) -> bool:
    return any(str(account_code).startswith(prefix) for prefix in ACCOUNT_PREFIXES.get(statement, ()))


def ingest_cvm_year(db: SupabaseRest, doc: str, year: int) -> None:
    doc = doc.upper()
    if doc not in {'DFP','ITR'}:
        raise ValueError('doc deve ser DFP ou ITR')
    url = CVM_URL.format(doc=doc, doc_lower=doc.lower(), year=year)
    run = IngestionRun(db, f'CVM_{doc}', source_url=url, run_key=str(year), metadata={'year':year,'document':doc})
    try:
        payload = http_bytes(url, timeout=240)
        digest = sha256(payload)
        issuers = db.select('lgv_issuers', 'select=id,code_cvm&code_cvm=not.is.null')
        issuer_map = {int(x['code_cvm']): x['id'] for x in issuers}
        rows = []
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            for name in zf.namelist():
                parsed = _statement_from_name(name)
                if not parsed or not name.lower().endswith('.csv'):
                    continue
                statement, scope = parsed
                raw_text = zf.read(name).decode('latin-1', errors='replace')
                reader = csv.DictReader(io.StringIO(raw_text), delimiter=';')
                for r in reader:
                    run.rows_read += 1
                    account = str(r.get('CD_CONTA') or '').strip()
                    if not _interesting(statement, account):
                        continue
                    try: code_cvm = int(str(r.get('CD_CVM') or '').strip())
                    except ValueError: continue
                    period_end = parse_date(r.get('DT_REFER'))
                    if not period_end:
                        continue
                    try: version = int(str(r.get('VERSAO') or '0').strip() or 0)
                    except ValueError: version = 0
                    rows.append({
                        'issuer_id': issuer_map.get(code_cvm), 'code_cvm': code_cvm,
                        'cnpj': r.get('CNPJ_CIA'), 'document_type': doc, 'document_version': version,
                        'period_end': period_end, 'period_start': parse_date(r.get('DT_INI_EXERC')),
                        'statement': statement, 'scope': scope, 'account_code': account,
                        'account_desc': r.get('DS_CONTA'), 'amount': parse_decimal(r.get('VL_CONTA')),
                        'currency': r.get('MOEDA'), 'scale': r.get('ESCALA_MOEDA'),
                        'exercise_order': r.get('ORDEM_EXERC'), 'source': f'CVM_{doc}', 'source_grade':'A',
                        'source_url': url,
                    })
        run.rows_written = db.upsert(
            'lgv_cvm_financial_lines', rows,
            'code_cvm,document_type,document_version,period_end,statement,scope,account_code,exercise_order',
            batch_size=750
        )
        run.success(digest, {'year':year,'document':doc,'selected_lines':len(rows)})
    except Exception as exc:
        run.fail(exc)
        raise
