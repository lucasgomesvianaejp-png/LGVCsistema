from __future__ import annotations

import io, re, zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Any

from .common import FirestoreRepo, IngestionRun, b64_params, date_after, http_bytes, http_json, parse_date, parse_decimal, sha256, utc_now_iso

COTAHIST_URL='https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP'
B3_PROXY='https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall'


def _num(line,start,end,decimals=0):
    raw=line[start-1:end].strip() or '0'; return int(raw)/(10**decimals)
def _txt(line,start,end): return line[start-1:end].strip()

def is_equity_spec(spec,isin):
    s=(spec or '').upper().strip()
    if 'BDR' in s or 'DRN' in s or 'DR1' in s or s=='CI': return False
    return bool(re.search(r'(^|\s)(ON|PN|PNA|PNB|PNC|PND|UNT)(\s|$)',s)) and str(isin).startswith('BR')

def parse_cotahist_line(line: str) -> dict[str,Any]|None:
    if len(line)<245 or line[:2]!='01': return None
    market_type=int(_txt(line,25,27) or 0)
    if market_type!=10: return None
    ticker=_txt(line,13,24).upper(); spec=_txt(line,40,49); isin=_txt(line,231,242)
    if not ticker or not is_equity_spec(spec,isin): return None
    factor=int(_txt(line,211,217) or 1) or 1
    return {'ticker':ticker,'date':parse_date(_txt(line,3,10)),'companyName':_txt(line,28,39),'shareClass':spec,
            'close':_num(line,109,121,2)/factor,'financialVolume':_num(line,171,188,2),'isin':isin,
            'quoteFactor':factor,'issuingCompanyGuess':ticker[:4]}

def _download_year(year:int):
    url=COTAHIST_URL.format(year=year); payload=http_bytes(url,timeout=240)
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        name=next((n for n in zf.namelist() if n.upper().endswith('.TXT')),None)
        if not name: raise RuntimeError(f'COTAHIST {year} sem TXT')
        lines=zf.read(name).decode('latin-1',errors='replace').splitlines()
    rows=[]
    for line in lines:
        rec=parse_cotahist_line(line)
        if rec and rec['date']: rows.append(rec)
    return url,payload,rows

def _catalog_results(body):
    if isinstance(body,dict):
        for key in ('results','companies','data'):
            if isinstance(body.get(key),list): return body[key]
    return body if isinstance(body,list) else []

def fetch_company_catalog():
    companies=[]; page=1
    while True:
        params={'language':'pt-br','pageNumber':page,'pageSize':120}
        body=http_json(f'{B3_PROXY}/GetInitialCompanies/{b64_params(params)}')
        rows=_catalog_results(body)
        if not rows: break
        companies.extend(rows)
        total=None
        if isinstance(body,dict):
            pi=body.get('page') or body.get('pagination') or {}; total=pi.get('totalPages') or body.get('totalPages')
        if (total and page>=int(total)) or len(rows)<120: break
        page += 1
        if page>100: break
    return companies

def ingest_company_catalog(db: FirestoreRepo):
    run=IngestionRun(db,'B3_LISTED_CATALOG',source_url=f'{B3_PROXY}/GetInitialCompanies')
    try:
        raw=fetch_company_catalog(); run.rows_read=len(raw); rows=[]
        for item in raw:
            code=item.get('codeCVM') or item.get('codeCvm')
            try: code=int(code) if code not in (None,'') else None
            except: code=None
            issuing=str(item.get('issuingCompany') or item.get('code') or '').strip().upper()
            if not issuing: continue
            rows.append((issuing,{'issuingCompany':issuing,'codeCvm':code,'tradingName':item.get('tradingName'),
                'companyName':item.get('companyName') or item.get('company'),'cnpj':item.get('cnpj'),
                'b3CompanyId':str(item.get('id') or item.get('companyId') or '') or None,
                'source':'B3_LISTED','sourceGrade':'A','updatedAt':utc_now_iso()}))
        run.rows_written=db.batch_set('researchIssuers',rows)
        run.success(metadata={'issuers':len(rows)}); return {k:v for k,v in rows}
    except Exception as exc: run.fail(exc); raise

def ingest_market_years(db: FirestoreRepo, years:list[int], rolling_12m:bool=True):
    run=IngestionRun(db,'B3_COTAHIST',source_url=COTAHIST_URL,run_key='-'.join(map(str,years)),metadata={'years':years})
    try:
        by_ticker=defaultdict(list); digests=[]; urls=[]
        for year in sorted(set(years)):
            url,payload,rows=_download_year(year); urls.append(url); digests.append(sha256(payload)); run.rows_read += len(rows)
            for r in rows: by_ticker[r['ticker']].append(r)
        issuers={x['id']:x for x in db.all('researchIssuers')}
        existing={x['id']:x for x in db.all('researchMarket')}
        asset_rows=[]; market_rows=[]
        max_date=max((date.fromisoformat(r['date']) for arr in by_ticker.values() for r in arr), default=None)
        cutoff=max_date-timedelta(days=365) if max_date else None
        for ticker,rows in by_ticker.items():
            rows.sort(key=lambda x:x['date']); last=rows[-1]; by_year=defaultdict(list)
            for r in rows: by_year[int(r['date'][:4])].append(r)
            old=existing.get(ticker,{}) or {}; year_map=dict(old.get('years') or {})
            for y,yr in by_year.items():
                year_map[str(y)]={'averageClose':sum(x['close'] for x in yr)/len(yr),'averageFinancialVolume':sum(x['financialVolume'] for x in yr)/len(yr),
                                  'tradingDays':len(yr),'lastClose':yr[-1]['close'],'lastDate':yr[-1]['date']}
            rolling=[r for r in rows if cutoff and date.fromisoformat(r['date'])>cutoff]
            adtv=sum(r['financialVolume'] for r in rolling)/len(rolling) if rolling else None
            issuer=issuers.get(last['issuingCompanyGuess'],{})
            asset_rows.append((ticker,{'ticker':ticker,'companyName':last['companyName'] or ticker,'issuingCompany':last['issuingCompanyGuess'],
                'codeCvm':issuer.get('codeCvm'),'shareClass':last['shareClass'],'isin':last['isin'],'assetClass':'ACAO','isActive':True,
                'source':'B3_COTAHIST','sourceGrade':'A','updatedAt':utc_now_iso()}))
            market_rows.append((ticker,{'ticker':ticker,'lastPrice':last['close'],'lastPriceDate':last['date'],'adtv12m':adtv,
                'years':year_map,'source':'B3_COTAHIST','sourceGrade':'A','sourceYears':sorted(int(y) for y in year_map),'updatedAt':utc_now_iso()}))
        run.rows_written=db.batch_set('researchAssets',asset_rows)+db.batch_set('researchMarket',market_rows)
        run.success(sha256(''.join(digests).encode()),{'assets':len(asset_rows),'maxDate':max_date.isoformat() if max_date else None,'urls':urls})
    except Exception as exc: run.fail(exc); raise

def fetch_company_supplement(issuing_company:str):
    params={'issuingCompany':issuing_company,'language':'pt-br'}
    body=http_json(f'{B3_PROXY}/GetListedSupplementCompany/{b64_params(params)}')
    return body if isinstance(body,dict) else {}

def ingest_company_supplements(db: FirestoreRepo, workers:int=6):
    run=IngestionRun(db,'B3_LISTED_SUPPLEMENT',source_url=f'{B3_PROXY}/GetListedSupplementCompany')
    try:
        issuers=[x for x in db.all('researchIssuers') if x.get('issuingCompany')]
        assets=db.all('researchAssets'); isin_to_ticker={str(a.get('isin') or '').upper():a['ticker'] for a in assets if a.get('isin')}
        tracked={a.get('issuingCompany') for a in assets if a.get('issuingCompany')}
        targets=[i for i in issuers if i['issuingCompany'] in tracked]
        results={}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs={pool.submit(fetch_company_supplement,i['issuingCompany']):i for i in targets}
            for fut in as_completed(futs):
                issuer=futs[fut]
                try: results[issuer['issuingCompany']]=(issuer,fut.result())
                except Exception as exc: results[issuer['issuingCompany']]=(issuer,{'_error':str(exc)})
        div_by_ticker=defaultdict(list); act_by_ticker=defaultdict(list); issuer_rows=[]
        for issuing,(issuer,body) in results.items():
            if body.get('_error'): continue
            info=body.get('info') if isinstance(body.get('info'),dict) else body
            issuer_rows.append((issuing,{'tradingName':info.get('tradingName') or issuer.get('tradingName'),'segment':info.get('segment'),
                'roundLot':int(parse_decimal(info.get('roundLot')) or 0) or None,'commonShares':parse_decimal(info.get('numberCommonShares')),
                'preferredShares':parse_decimal(info.get('numberPreferredShares')),'totalShares':parse_decimal(info.get('totalNumberShares')),
                'supplementRefDate':parse_date(info.get('refdate')),'source':'B3_LISTED','sourceGrade':'A','updatedAt':utc_now_iso()}))
            for e in body.get('cashDividends') or []:
                isin=str(e.get('isinCode') or e.get('assetIssued') or '').strip().upper(); ticker=isin_to_ticker.get(isin)
                ex_date=parse_date(e.get('exDate')) or date_after(e.get('lastDatePrior')); amount=parse_decimal(e.get('rate'))
                if not ticker or not ex_date or amount is None: continue
                div_by_ticker[ticker].append({'exDate':ex_date,'declaredDate':parse_date(e.get('approvedOn')),'paymentDate':parse_date(e.get('paymentDate')),
                    'eventType':str(e.get('label') or 'PROVENTO').upper(),'amountPerShare':amount,'referencePeriod':e.get('relatedTo'),
                    'observations':e.get('remarks'),'recurrenceClass':'PENDING','isin':isin})
            for e in body.get('stockDividends') or []:
                isin=str(e.get('isinCode') or '').strip().upper(); ticker=isin_to_ticker.get(isin)
                event_date=parse_date(e.get('exDate')) or date_after(e.get('lastDatePrior')) or parse_date(e.get('approvedOn')); factor=parse_decimal(e.get('factor'))
                if not ticker or not event_date or factor is None: continue
                act_by_ticker[ticker].append({'eventDate':event_date,'actionType':str(e.get('label') or 'CORPORATE_ACTION').upper(),'factor':factor,
                    'emittedIsin':e.get('assetIssued'),'observations':e.get('remarks'),'isin':isin})
        div_rows=[]; act_rows=[]
        for a in assets:
            ticker=a['ticker']; events=sorted(div_by_ticker.get(ticker,[]),key=lambda x:x['exDate'])
            annual=defaultdict(float)
            for e in events: annual[e['exDate'][:4]] += float(e['amountPerShare'])
            div_rows.append((ticker,{'ticker':ticker,'events':events,'annualRaw':dict(annual),'source':'B3_LISTED','sourceGrade':'A','updatedAt':utc_now_iso()}))
            actions=sorted(act_by_ticker.get(ticker,[]),key=lambda x:x['eventDate'])
            act_rows.append((ticker,{'ticker':ticker,'events':actions,'source':'B3_LISTED','sourceGrade':'A','updatedAt':utc_now_iso()}))
        run.rows_read=sum(len(v) for v in div_by_ticker.values())+sum(len(v) for v in act_by_ticker.values())
        run.rows_written=db.batch_set('researchIssuers',issuer_rows)+db.batch_set('researchDividends',div_rows)+db.batch_set('researchCorporateActions',act_rows)
        run.success(metadata={'issuersChecked':len(targets),'dividendTickers':len(div_by_ticker),'actionTickers':len(act_by_ticker)})
    except Exception as exc: run.fail(exc); raise
