from __future__ import annotations
import csv, io, zipfile
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any
from .common import FirestoreRepo, IngestionRun, http_bytes, parse_date, parse_decimal, sha256, utc_now_iso

CVM_URL='https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{doc}/DADOS/{doc_lower}_cia_aberta_{year}.zip'
ACCOUNT_PREFIXES={'DRE':('3.01','3.05','3.11'),'BPA':('1.01',),'BPP':('2.01.04','2.02.01','2.03'),'DFC_MI':('6.01','6.02'),'DFC_MD':('6.01','6.02')}

def _statement_from_name(name):
    upper=PurePosixPath(name).name.upper()
    for st in ('DFC_MI','DFC_MD','DRE','BPA','BPP'):
        if f'_{st}_CON_' in upper:return st,'CON'
        if f'_{st}_IND_' in upper:return st,'IND'
    return None

def _interesting(st,account): return any(str(account).startswith(p) for p in ACCOUNT_PREFIXES.get(st,()))

def _scaled(amount,scale):
    if amount is None:return None
    s=str(scale or '').upper()
    if 'MIL' in s:return amount*1000.0
    if 'MILH' in s:return amount*1_000_000.0
    return amount

def ingest_cvm_year(db: FirestoreRepo, doc: str, year:int):
    doc=doc.upper()
    if doc not in {'DFP','ITR'}: raise ValueError('doc deve ser DFP ou ITR')
    url=CVM_URL.format(doc=doc,doc_lower=doc.lower(),year=year)
    run=IngestionRun(db,f'CVM_{doc}',source_url=url,run_key=str(year),metadata={'year':year,'document':doc})
    try:
        payload=http_bytes(url,timeout=300); digest=sha256(payload); grouped=defaultdict(dict); latest_profit={}
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            for name in zf.namelist():
                parsed=_statement_from_name(name)
                if not parsed or not name.lower().endswith('.csv'):continue
                statement,scope=parsed
                reader=csv.DictReader(io.StringIO(zf.read(name).decode('latin-1',errors='replace')),delimiter=';')
                for r in reader:
                    run.rows_read += 1; account=str(r.get('CD_CONTA') or '').strip()
                    if not _interesting(statement,account):continue
                    try: code=int(str(r.get('CD_CVM') or '').strip())
                    except: continue
                    period_end=parse_date(r.get('DT_REFER'))
                    if not period_end:continue
                    try: version=int(str(r.get('VERSAO') or '0').strip() or 0)
                    except: version=0
                    key=f'{doc}_{period_end}_{scope}'
                    g=grouped[code].setdefault(key,{'documentType':doc,'documentVersion':version,'periodEnd':period_end,'periodStart':parse_date(r.get('DT_INI_EXERC')),
                        'scope':scope,'accounts':{},'sourceUrl':url})
                    # Reapresentação: mantém maior versão por período.
                    if version < int(g.get('documentVersion') or 0): continue
                    if version > int(g.get('documentVersion') or 0): g['accounts']={}; g['documentVersion']=version
                    amount=parse_decimal(r.get('VL_CONTA'))
                    g['accounts'][f'{statement}:{account}:{r.get("ORDEM_EXERC") or ""}']={'statement':statement,'accountCode':account,'accountDesc':r.get('DS_CONTA'),
                        'amount':amount,'scale':r.get('ESCALA_MOEDA'),'exerciseOrder':r.get('ORDEM_EXERC')}
                    if doc=='DFP' and scope=='CON' and statement=='DRE' and account=='3.11' and str(r.get('ORDEM_EXERC') or '').upper() in {'ÚLTIMO','ULTIMO','LAST',''}:
                        val=_scaled(amount,r.get('ESCALA_MOEDA'))
                        old=latest_profit.get(code)
                        if val is not None and (not old or period_end>=old['periodEnd']): latest_profit[code]={'amount':val,'periodEnd':period_end,'documentVersion':version}
        existing={x['id']:x for x in db.all('researchFundamentals')}
        rows=[]
        for code,periods in grouped.items():
            old=existing.get(str(code),{}) or {}; merged=dict(old.get('periods') or {}); merged.update(periods)
            values={'codeCvm':code,'periods':merged,'source':f'CVM_{doc}','sourceGrade':'A','updatedAt':utc_now_iso()}
            if code in latest_profit: values['latestFyNetIncome']=latest_profit[code]['amount']; values['latestFyPeriodEnd']=latest_profit[code]['periodEnd']
            rows.append((str(code),values))
        run.rows_written=db.batch_set('researchFundamentals',rows); run.success(digest,{'issuers':len(rows),'selectedPeriods':sum(len(v) for v in grouped.values())})
    except Exception as exc: run.fail(exc); raise
