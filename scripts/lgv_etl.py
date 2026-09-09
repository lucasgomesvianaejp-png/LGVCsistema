#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lgv_data.common import SupabaseRest
from lgv_data.b3 import ingest_cash_dividends, ingest_company_catalog, ingest_cotahist_year
from lgv_data.cvm import ingest_cvm_year
from lgv_data.tesouro import ingest_tesouro


def parse_args():
    p = argparse.ArgumentParser(description='LGV Capital Research ETL')
    p.add_argument('source', choices=['daily','weekly','b3','b3-catalog','dividends','tesouro','cvm','all'])
    p.add_argument('--years', nargs='*', type=int, default=[])
    p.add_argument('--doc', choices=['DFP','ITR','both'], default='both')
    return p.parse_args()


def main():
    args = parse_args()
    db = SupabaseRest()
    current = date.today().year
    years = args.years or [current]

    if args.source in {'weekly','b3-catalog','all'}:
        ingest_company_catalog(db)
    if args.source in {'daily','b3','all'}:
        for year in years:
            ingest_cotahist_year(db, year)
    if args.source in {'daily','tesouro','all'}:
        ingest_tesouro(db)
    if args.source in {'weekly','dividends','all'}:
        ingest_cash_dividends(db)
    if args.source in {'weekly','cvm','all'}:
        docs = ['DFP','ITR'] if args.doc == 'both' else [args.doc]
        # DFP anual: últimos 5 exercícios completos; ITR: ano corrente por padrão.
        for doc in docs:
            doc_years = years
            if not args.years and doc == 'DFP':
                doc_years = list(range(current - 5, current))
            for year in doc_years:
                ingest_cvm_year(db, doc, year)


if __name__ == '__main__':
    main()
