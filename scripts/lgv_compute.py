#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(Path(__file__).resolve().parent))
from engine.screener import PreScreenInput,pre_screen
from lgv_data.common import FirestoreRepo,utc_now_iso

def main():
    p=argparse.ArgumentParser(); p.add_argument('--as-of',default=date.today().isoformat()); args=p.parse_args(); as_of=date.fromisoformat(args.as_of)
    cfg=json.loads((ROOT/'config/research_methodology.json').read_text()); version=cfg['pre_screen_version']; complete=int(cfg['complete_years']); years=list(range(as_of.year-complete,as_of.year))
    db=FirestoreRepo(); assets=db.all('researchAssets'); market={x['id']:x for x in db.all('researchMarket')}; divs={x['id']:x for x in db.all('researchDividends')}; acts={x['id']:x for x in db.all('researchCorporateActions')}; funds={x['id']:x for x in db.all('researchFundamentals')}
    items=[]; counts={}
    for a in assets:
        ticker=a.get('ticker') or a['id']; m=market.get(ticker,{}) or {}; d=divs.get(ticker,{}) or {}; annual=d.get('annualRaw') or {}; year_stats=m.get('years') or {}; dys=[]; dividend_years=0
        for y in years:
            price=(year_stats.get(str(y)) or {}).get('averageClose'); dpa=annual.get(str(y))
            if price and dpa is not None:
                dys.append(float(dpa)/float(price)); dividend_years += 1
        raw_dy=sum(dys)/len(dys) if len(dys)==complete else None
        corporate=acts.get(ticker,{}) or {}; has_action=any(int(str(e.get('eventDate','0000'))[:4] or 0) in years for e in corporate.get('events') or [])
        code=a.get('codeCvm'); f=funds.get(str(code),{}) if code is not None else {}; profit=f.get('latestFyNetIncome')
        result=pre_screen(PreScreenInput(ticker=ticker,sector=a.get('sector'),adtv_12m=m.get('adtv12m'),raw_dy_5y=raw_dy,latest_profit=profit,has_corporate_action_5y=has_action,dividend_years=dividend_years),
            liquidity_min=float(cfg['liquidity_min_adtv_brl']),liquidity_near=float(cfg['liquidity_near_adtv_brl']),dy_min=float(cfg['dy_5y_min']),dy_near=float(cfg['dy_5y_near']),complete_years=complete,excluded_sector_terms=tuple(cfg['excluded_sector_terms']))
        item={'ticker':ticker,'company':a.get('companyName') or ticker,'sector':a.get('sector') or 'Não classificado','adtv12m':m.get('adtv12m'),'dy5y':raw_dy,
              'profitPositive':result.passes_profit,'marketPrice':m.get('lastPrice'),'status':result.status,'failReasons':list(result.fail_reasons),'nearReasons':list(result.near_reasons)}
        items.append(item); counts[result.status]=counts.get(result.status,0)+1
    items.sort(key=lambda x:(x['status'],x['ticker']))
    snapshot={'snapshotDate':args.as_of,'methodologyVersion':version,'items':items,'counts':counts,'computedAt':utc_now_iso()}
    db.set('researchScreeningSnapshots',args.as_of,snapshot,merge=False); db.set('researchScreening','current',snapshot,merge=False)
    print(json.dumps({'asOf':args.as_of,'assets':len(items),'status':counts},ensure_ascii=False))
if __name__=='__main__': main()
