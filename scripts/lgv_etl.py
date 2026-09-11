#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from lgv_data.common import FirestoreRepo
from lgv_data.b3 import ingest_company_catalog, ingest_company_supplements, ingest_market_years
from lgv_data.cvm import ingest_cvm_year
from lgv_data.tesouro import ingest_tesouro

def parse_args():
    p=argparse.ArgumentParser(description='LGV Capital Research ETL — Firebase')
    p.add_argument('mode',choices=['bootstrap','daily','weekly','market','cvm','dividends','tesouro'])
    p.add_argument('--years',nargs='*',type=int,default=[])
    return p.parse_args()
def main():
    args=parse_args(); db=FirestoreRepo(); current=date.today().year
    if args.mode=='bootstrap':
        ingest_company_catalog(db)
        ingest_market_years(db,args.years or list(range(current-5,current+1)))
        ingest_company_supplements(db)
        for y in range(current-5,current): ingest_cvm_year(db,'DFP',y)
        ingest_cvm_year(db,'ITR',current); ingest_tesouro(db)
    elif args.mode=='daily':
        ingest_market_years(db,args.years or [current-1,current]); ingest_tesouro(db)
    elif args.mode=='weekly':
        ingest_company_catalog(db); ingest_company_supplements(db)
        # Reapresentações e documentos novos: ano anterior + ano corrente são suficientes na rotina.
        for y in sorted({current-1,current}):
            try: ingest_cvm_year(db,'DFP',y)
            except Exception as exc: print(f'[WARN] DFP {y}: {exc}',file=sys.stderr)
        ingest_cvm_year(db,'ITR',current)
    elif args.mode=='market': ingest_market_years(db,args.years or [current-1,current])
    elif args.mode=='dividends': ingest_company_catalog(db); ingest_company_supplements(db)
    elif args.mode=='tesouro': ingest_tesouro(db)
    elif args.mode=='cvm':
        for y in args.years or [current]: ingest_cvm_year(db,'ITR',y)
if __name__=='__main__': main()
