import { requireFirebaseUser } from '../_lib/auth.js';
import { json, methodNotAllowed } from '../_lib/http.js';
import { supabaseGet } from '../_lib/supabase-rest.js';

function countFromRange(value) {
  const match = String(value || '').match(/\/(\d+|\*)$/);
  return match && match[1] !== '*' ? Number(match[1]) : null;
}

export default async function handler(req, res) {
  if (req.method !== 'GET') return methodNotAllowed(res);
  try {
    await requireFirebaseUser(req);
    const dashboard = await supabaseGet(
      'lgv_stock_dashboard_latest?select=*&order=opportunity_rank.asc.nullslast,ticker.asc'
    );
    const screenerResult = await supabaseGet(
      'lgv_screener_latest?select=*&order=screening_status.asc,ticker.asc'
    );
    const researchQueueResult = await supabaseGet(
      'lgv_research_queue_latest?select=*&order=priority_rank.desc,ticker.asc'
    );
    const universe = await supabaseGet(
      'lgv_assets?select=id&asset_class=eq.ACAO&is_active=eq.true&limit=1',
      { count: true }
    );
    const ingestion = await supabaseGet(
      'lgv_ingestion_runs?select=source,status,finished_at,rows_written,error_message&order=finished_at.desc.nullslast&limit=8'
    );

    const stocks = dashboard.data.map(row => ({
      ticker: row.ticker,
      company: row.display_name || row.company_name || row.ticker,
      sector: row.sector || 'Não classificado',
      floor: row.shelf_floor ? `${row.shelf_floor}º` : '—',
      rank: row.opportunity_rank,
      top15: Boolean(row.is_top15),
      portfolio: Boolean(row.is_theoretical_portfolio),
      auditGrade: row.audit_grade || 'C',
      priceStatus: row.price_status === 'COMPRA' ? 'Compra' : row.price_status === 'RAZOAVEL' ? 'Razoável' : row.price_status === 'CARA' ? 'Cara' : 'Pendente',
      qualityScore: row.quality_score == null ? null : Number(row.quality_score),
      priceScore: row.price_score == null ? null : Number(row.price_score),
      opportunityScore: row.opportunity_score == null ? null : Number(row.opportunity_score),
      pcLgv: row.pc_lgv == null ? null : Number(row.pc_lgv),
      marketPrice: row.market_price == null ? null : Number(row.market_price),
      fairValue: row.fair_value == null ? null : Number(row.fair_value),
      incomeCeiling: row.income_ceiling == null ? null : Number(row.income_ceiling),
      source: row.market_source || row.valuation_source || 'LGV Research DB',
      snapshotDate: row.snapshot_date || row.market_price_date || null,
      marketPriceDate: row.market_price_date || null,
      methodologyVersion: row.methodology_version || null,
      adtv12m: row.adtv_12m == null ? null : Number(row.adtv_12m),
      researchOpen: Number(row.open_research_flags || 0)
    }));

    const screener = screenerResult.data.map(row => ({
      ticker: row.ticker, company: row.display_name || row.company_name || row.ticker,
      sector: row.sector || 'Não classificado', marketPrice: row.market_price == null ? null : Number(row.market_price),
      marketPriceDate: row.market_price_date || null, adtv12m: row.adtv_12m == null ? null : Number(row.adtv_12m),
      dy5y: row.dy_5y == null ? null : Number(row.dy_5y), profitPositive: row.profit_positive,
      status: row.screening_status || 'PENDING', failReasons: row.fail_reasons || [], nearReasons: row.near_reasons || [],
      methodologyVersion: row.methodology_version || null, snapshotDate: row.snapshot_date || null
    }));

    const researchQueue = researchQueueResult.data.map(row => ({
      ticker: row.ticker,
      company: row.display_name || row.company_name || row.ticker,
      sector: row.sector || 'Não classificado',
      reason: row.reason,
      priority: row.priority || 'MEDIUM',
      snapshotDate: row.snapshot_date || null,
      methodologyVersion: row.methodology_version || null
    }));

    return json(res, 200, {
      stocks,
      screener,
      researchQueue,
      meta: {
        universeCount: countFromRange(universe.contentRange) ?? stocks.length,
        databaseMode: true,
        ingestion: ingestion.data
      }
    });
  } catch (error) {
    console.error('[research/stocks]', error);
    return json(res, error.statusCode || 500, { error: error.message || 'internal_error' });
  }
}
