from __future__ import annotations
import csv, io
from datetime import date
from typing import Any
from .common import FirestoreRepo, IngestionRun, http_bytes, parse_date, parse_decimal, sha256, utc_now_iso
TESOURO_CSV='https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv'
def _pick(row,*names):
    n={str(k).strip().lower():v for k,v in row.items()}
    for name in names:
        if name.lower() in n:return n[name.lower()]
def _rate(v):
    x=parse_decimal(v)
    return (x/100.0 if abs(x)>1 else x) if x is not None else None

def _eligible(title):
    t=str(title or '').lower()
    return 'ipca+' in t and 'renda+' not in t and 'educa+' not in t

def ingest_tesouro(db: FirestoreRepo):
    run=IngestionRun(db,'TESOURO_TD',source_url=TESOURO_CSV)
    try:
        payload=http_bytes(TESOURO_CSV,timeout=240); digest=sha256(payload); text=payload.decode('utf-8-sig',errors='replace'); delim=';' if text[:5000].count(';')>text[:5000].count(',') else ','
        records=[]
        for raw in csv.DictReader(io.StringIO(text),delimiter=delim):
            run.rows_read += 1; title=_pick(raw,'Tipo Titulo','Tipo Título','TipoTitulo'); base=parse_date(_pick(raw,'Data Base','DataBase')); maturity=parse_date(_pick(raw,'Data Vencimento','DataVencimento'))
            if not title or not base or not maturity:continue
            records.append({'rateDate':base,'titleType':str(title).strip(),'maturityDate':maturity,'buyRate':_rate(_pick(raw,'Taxa Compra Manha','Taxa Compra Manhã','TaxaCompraManha')),
                'sellRate':_rate(_pick(raw,'Taxa Venda Manha','Taxa Venda Manhã','TaxaVendaManha')),'buyPrice':parse_decimal(_pick(raw,'PU Compra Manha','PU Compra Manhã','PUCompraManha')),
                'sellPrice':parse_decimal(_pick(raw,'PU Venda Manha','PU Venda Manhã','PUVendaManha'))})
        latest=max((r['rateDate'] for r in records),default=None); options=[r for r in records if r['rateDate']==latest and _eligible(r['titleType']) and r['buyRate'] is not None]
        ref=max(options,key=lambda r:r['maturityDate']) if options else None
        required=None
        if ref: required=min(0.08,max(0.06,float(ref['buyRate'])+0.005))
        db.set('researchTreasury','current',{'rateDate':latest,'reference':ref,'requiredYieldLgv':required,'eligibleCount':len(options),'source':'TESOURO_TD','sourceGrade':'A','sourceUrl':TESOURO_CSV,'updatedAt':utc_now_iso()},merge=False)
        run.rows_written=1; run.success(digest,{'records':len(records),'reference':ref})
    except Exception as exc: run.fail(exc); raise
