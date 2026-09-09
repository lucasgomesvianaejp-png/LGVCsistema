#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.screener import PreScreenInput, pre_screen
from lgv_data.common import SupabaseRest


def args_parser():
    p = argparse.ArgumentParser(description='Calcula o pré-screening LGV a partir do banco.')
    p.add_argument('--as-of', default=date.today().isoformat())
    return p.parse_args()


def money_scale(amount, scale):
    if amount is None: return None
    text = str(scale or '').upper()
    if 'MIL' in text: return float(amount) * 1000.0
    if 'MILHAO' in text or 'MILHÃO' in text: return float(amount) * 1_000_000.0
    return float(amount)


def main():
    args = args_parser()
    as_of = date.fromisoformat(args.as_of)
    cfg = json.loads((ROOT / 'config/research_methodology.json').read_text())
    version = cfg['pre_screen_version']
    complete_years = int(cfg['complete_years'])
    years = list(range(as_of.year - complete_years, as_of.year))

    db = SupabaseRest()
    assets = db.select_all('lgv_assets', 'select=id,ticker,sector,code_cvm&asset_class=eq.ACAO&is_active=eq.true')
    market = {x['asset_id']: x for x in db.select_all('lgv_market_stats_12m', 'select=asset_id,adtv_12m')}
    annual_prices = db.select_all('lgv_price_stats_annual', 'select=asset_id,year,average_close')
    annual_divs = db.select_all('lgv_dividend_stats_annual_raw', 'select=asset_id,year,dpa_raw')
    actions = db.select_all('lgv_corporate_actions', 'select=asset_id,event_date&asset_id=not.is.null')
    profits = db.select_all('lgv_latest_fy_net_income', 'select=code_cvm,amount,scale,period_end')

    price_map = {(x['asset_id'], int(x['year'])): float(x['average_close']) for x in annual_prices if x.get('average_close') is not None}
    div_map = {(x['asset_id'], int(x['year'])): float(x['dpa_raw']) for x in annual_divs if x.get('dpa_raw') is not None}
    action_assets = set()
    for x in actions:
        if not x.get('asset_id') or not x.get('event_date'): continue
        y = int(str(x['event_date'])[:4])
        if y in years: action_assets.add(x['asset_id'])
    profit_map = {int(x['code_cvm']): money_scale(x.get('amount'), x.get('scale')) for x in profits if x.get('code_cvm') is not None}

    output = []
    for asset in assets:
        dys = []
        dividend_years = 0
        for year in years:
            price = price_map.get((asset['id'], year))
            dpa = div_map.get((asset['id'], year))
            if price and price > 0 and dpa is not None:
                dys.append(dpa / price)
                dividend_years += 1
        raw_dy = sum(dys) / len(dys) if len(dys) == complete_years else None
        adtv = market.get(asset['id'], {}).get('adtv_12m')
        adtv = float(adtv) if adtv is not None else None
        profit = profit_map.get(int(asset['code_cvm'])) if asset.get('code_cvm') is not None else None
        result = pre_screen(
            PreScreenInput(
                ticker=asset['ticker'], sector=asset.get('sector'), adtv_12m=adtv,
                raw_dy_5y=raw_dy, latest_profit=profit,
                has_corporate_action_5y=asset['id'] in action_assets,
                dividend_years=dividend_years,
            ),
            liquidity_min=float(cfg['liquidity_min_adtv_brl']),
            liquidity_near=float(cfg['liquidity_near_adtv_brl']),
            dy_min=float(cfg['dy_5y_min']), dy_near=float(cfg['dy_5y_near']),
            complete_years=complete_years,
            excluded_sector_terms=tuple(cfg['excluded_sector_terms']),
        )
        output.append({
            'snapshot_date': as_of.isoformat(), 'methodology_version': version, 'asset_id': asset['id'],
            'adtv_12m': adtv, 'dy_5y': raw_dy, 'profit_positive': result.passes_profit,
            'passes_liquidity': result.passes_liquidity, 'passes_dividend': result.passes_dividend,
            'passes_profit': result.passes_profit, 'passes_quality_reference': None,
            'screening_status': result.status, 'fail_reasons': list(result.fail_reasons),
            'near_reasons': list(result.near_reasons),
        })
    db.upsert('lgv_screening_snapshots', output, 'snapshot_date,methodology_version,asset_id', batch_size=500)
    counts = defaultdict(int)
    for x in output: counts[x['screening_status']] += 1
    print(json.dumps({'as_of': args.as_of, 'version': version, 'assets': len(output), 'status': dict(counts)}, ensure_ascii=False))


if __name__ == '__main__': main()
