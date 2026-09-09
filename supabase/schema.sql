-- LGV Capital Research Data Layer v2
-- Banco de research separado logicamente do módulo legado de clientes.
-- O frontend NUNCA recebe service_role. A API server-side é a única ponte.

create extension if not exists pgcrypto;

create table if not exists public.lgv_data_sources (
  source_code text primary key,
  source_name text not null,
  source_type text not null,
  base_url text,
  default_grade char(1) not null default 'A' check (default_grade in ('A','B','C','D')),
  is_active boolean not null default true,
  notes text,
  updated_at timestamptz not null default now()
);

insert into public.lgv_data_sources(source_code, source_name, source_type, base_url, default_grade, notes)
values
 ('B3_COTAHIST','B3 Cotações Históricas','MARKET','https://bvmf.bmfbovespa.com.br/InstDados/SerHist/','A','Arquivo oficial anual COTAHIST.'),
 ('B3_LISTED','B3 Empresas Listadas','CORPORATE_ACTIONS','https://sistemaswebb3-listados.b3.com.br/','A','Catálogo de emissores e proventos em dinheiro.'),
 ('CVM_DFP','CVM DFP','FINANCIALS','https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/','A','Demonstrações financeiras padronizadas.'),
 ('CVM_ITR','CVM ITR','FINANCIALS','https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/','A','Informações trimestrais.'),
 ('TESOURO_TD','Tesouro Transparente - Tesouro Direto','RATES','https://www.tesourotransparente.gov.br/','A','Taxas e preços do Tesouro Direto.')
on conflict (source_code) do update set
 source_name=excluded.source_name, source_type=excluded.source_type,
 base_url=excluded.base_url, default_grade=excluded.default_grade,
 notes=excluded.notes, updated_at=now();

create table if not exists public.lgv_ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  run_key text,
  status text not null default 'RUNNING' check (status in ('RUNNING','SUCCESS','FAILED','PARTIAL','SKIPPED')),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  rows_read bigint not null default 0,
  rows_written bigint not null default 0,
  source_url text,
  source_hash text,
  error_message text,
  metadata jsonb not null default '{}'::jsonb
);
create index if not exists idx_lgv_ingestion_runs_source_started on public.lgv_ingestion_runs(source, started_at desc);

create table if not exists public.lgv_issuers (
  id uuid primary key default gen_random_uuid(),
  code_cvm integer unique,
  issuing_company text,
  trading_name text,
  company_name text,
  cnpj text,
  b3_company_id text,
  segment text,
  round_lot integer,
  common_shares numeric(24,4),
  preferred_shares numeric(24,4),
  total_shares numeric(24,4),
  quoted_since date,
  supplement_ref_date date,
  source text not null default 'B3_LISTED',
  source_grade char(1) not null default 'A' check (source_grade in ('A','B','C','D')),
  updated_at timestamptz not null default now()
);
create unique index if not exists uq_lgv_issuers_issuing_company on public.lgv_issuers(issuing_company) where issuing_company is not null;

create table if not exists public.lgv_assets (
  id uuid primary key default gen_random_uuid(),
  issuer_id uuid references public.lgv_issuers(id) on delete set null,
  ticker text not null unique,
  company_name text not null,
  display_name text,
  cnpj text,
  code_cvm integer,
  asset_class text not null default 'ACAO',
  sector text,
  subsector text,
  share_class text,
  isin text,
  bdi_code text,
  quote_factor integer,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_lgv_assets_issuer on public.lgv_assets(issuer_id);
create index if not exists idx_lgv_assets_isin on public.lgv_assets(isin);

create table if not exists public.lgv_market_prices (
  asset_id uuid not null references public.lgv_assets(id) on delete cascade,
  price_date date not null,
  open numeric(20,8),
  high numeric(20,8),
  low numeric(20,8),
  average numeric(20,8),
  close numeric(20,8) not null,
  trades integer,
  quantity numeric(24,4),
  financial_volume numeric(24,2),
  isin text,
  quote_factor integer,
  market_type integer,
  source text not null,
  source_grade char(1) not null default 'C' check (source_grade in ('A','B','C','D')),
  source_url text,
  ingested_at timestamptz not null default now(),
  primary key (asset_id, price_date)
);
create index if not exists idx_lgv_prices_asset_date on public.lgv_market_prices(asset_id, price_date desc);
create index if not exists idx_lgv_prices_date on public.lgv_market_prices(price_date desc);

create table if not exists public.lgv_treasury_rates (
  rate_date date not null,
  title_type text not null,
  maturity_date date not null,
  buy_rate numeric(12,8),
  sell_rate numeric(12,8),
  buy_price numeric(20,8),
  sell_price numeric(20,8),
  source text not null default 'TESOURO_TD',
  source_grade char(1) not null default 'A' check (source_grade in ('A','B','C','D')),
  source_url text,
  ingested_at timestamptz not null default now(),
  primary key (rate_date, title_type, maturity_date)
);
create index if not exists idx_lgv_treasury_date on public.lgv_treasury_rates(rate_date desc, maturity_date desc);

create table if not exists public.lgv_cvm_financial_lines (
  id bigint generated always as identity primary key,
  issuer_id uuid references public.lgv_issuers(id) on delete set null,
  code_cvm integer not null,
  cnpj text,
  document_type text not null check (document_type in ('DFP','ITR')),
  document_version integer,
  period_end date not null,
  period_start date,
  statement text not null,
  scope text not null check (scope in ('CON','IND')),
  account_code text not null,
  account_desc text,
  amount numeric(28,4),
  currency text,
  scale text,
  exercise_order text,
  source text not null,
  source_grade char(1) not null default 'A' check (source_grade in ('A','B','C','D')),
  source_url text,
  ingested_at timestamptz not null default now(),
  unique (code_cvm, document_type, document_version, period_end, statement, scope, account_code, exercise_order)
);
create index if not exists idx_lgv_cvm_lines_company_period on public.lgv_cvm_financial_lines(code_cvm, period_end desc);
create index if not exists idx_lgv_cvm_lines_account on public.lgv_cvm_financial_lines(account_code, statement);

create table if not exists public.lgv_financial_periods (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.lgv_assets(id) on delete cascade,
  period_end date not null,
  period_type text not null check (period_type in ('FY','Q','YTD','TTM')),
  revenue numeric(24,2),
  ebit numeric(24,2),
  net_income numeric(24,2),
  equity numeric(24,2),
  gross_debt numeric(24,2),
  cash numeric(24,2),
  operating_cash_flow numeric(24,2),
  capex numeric(24,2),
  diluted_shares numeric(24,4),
  source text not null,
  source_grade char(1) not null default 'C' check (source_grade in ('A','B','C','D')),
  ingested_at timestamptz not null default now(),
  unique (asset_id, period_end, period_type)
);
create index if not exists idx_lgv_financials_asset_period on public.lgv_financial_periods(asset_id, period_end desc);

create table if not exists public.lgv_dividends (
  id uuid primary key default gen_random_uuid(),
  issuer_id uuid references public.lgv_issuers(id) on delete cascade,
  asset_id uuid references public.lgv_assets(id) on delete cascade,
  isin text,
  declared_date date,
  ex_date date not null,
  payment_date date,
  event_type text not null,
  amount_per_share numeric(20,10) not null,
  reference_period text,
  observations text,
  recurrence_class text not null default 'PENDING' check (recurrence_class in ('RECURRING','EXTRAORDINARY','UNCERTAIN','PENDING')),
  source text not null,
  source_grade char(1) not null default 'C' check (source_grade in ('A','B','C','D')),
  source_url text,
  research_note text,
  ingested_at timestamptz not null default now(),
  unique (isin, ex_date, event_type, amount_per_share)
);
create index if not exists idx_lgv_dividends_asset_ex on public.lgv_dividends(asset_id, ex_date desc);
create index if not exists idx_lgv_dividends_issuer_ex on public.lgv_dividends(issuer_id, ex_date desc);

create table if not exists public.lgv_corporate_actions (
  id uuid primary key default gen_random_uuid(),
  issuer_id uuid references public.lgv_issuers(id) on delete cascade,
  asset_id uuid references public.lgv_assets(id) on delete cascade,
  isin text,
  event_date date not null,
  action_type text not null,
  factor numeric(20,10),
  emitted_isin text,
  observations text,
  source text not null,
  source_grade char(1) not null default 'A' check (source_grade in ('A','B','C','D')),
  source_url text,
  ingested_at timestamptz not null default now(),
  unique (isin, event_date, action_type, factor)
);

create table if not exists public.lgv_metrics (
  asset_id uuid not null references public.lgv_assets(id) on delete cascade,
  metric_date date not null,
  roe numeric(12,6),
  roic numeric(12,6),
  net_debt_ebitda numeric(12,6),
  eps_ttm numeric(20,8),
  eps_normalized numeric(20,8),
  eps_cagr_5y numeric(12,6),
  raw_dpa_5y numeric(20,8),
  dpa_5y numeric(20,8),
  dy_5y numeric(12,8),
  payout_sustainable numeric(12,6),
  dpa_fundamental numeric(20,8),
  dpa_lgv numeric(20,8),
  adtv_12m numeric(24,2),
  audit_grade char(1) not null default 'C' check (audit_grade in ('A','B','C')),
  methodology_version text not null,
  computed_at timestamptz not null default now(),
  primary key (asset_id, metric_date, methodology_version)
);

create table if not exists public.lgv_screening_snapshots (
  snapshot_date date not null,
  methodology_version text not null,
  asset_id uuid not null references public.lgv_assets(id) on delete cascade,
  adtv_12m numeric(24,2),
  dy_5y numeric(12,8),
  roe numeric(12,6),
  roic numeric(12,6),
  net_debt_ebitda numeric(12,6),
  profit_positive boolean,
  passes_liquidity boolean,
  passes_dividend boolean,
  passes_profit boolean,
  passes_quality_reference boolean,
  screening_status text not null default 'PENDING' check (screening_status in ('PASS','NEAR','FAIL','PENDING')),
  fail_reasons jsonb not null default '[]'::jsonb,
  near_reasons jsonb not null default '[]'::jsonb,
  computed_at timestamptz not null default now(),
  primary key (snapshot_date, methodology_version, asset_id)
);

create table if not exists public.lgv_valuations (
  asset_id uuid not null references public.lgv_assets(id) on delete cascade,
  valuation_date date not null,
  methodology_version text not null,
  required_yield numeric(12,8),
  income_ceiling numeric(20,8),
  historical_pe numeric(12,6),
  international_pe numeric(12,6),
  brazil_factor numeric(12,8),
  fair_pe numeric(12,6),
  fair_value numeric(20,8),
  pc_lgv numeric(20,8),
  market_price numeric(20,8),
  price_status text check (price_status in ('COMPRA','RAZOAVEL','CARA','PENDENTE')),
  quality_score numeric(8,4),
  price_score numeric(8,4),
  opportunity_score numeric(8,4),
  audit_grade char(1) not null default 'C' check (audit_grade in ('A','B','C')),
  source text default 'LGV_ENGINE',
  computed_at timestamptz not null default now(),
  primary key (asset_id, valuation_date, methodology_version)
);

create table if not exists public.lgv_research_flags (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.lgv_assets(id) on delete cascade,
  opened_at timestamptz not null default now(),
  flag_type text not null,
  severity text not null default 'MEDIUM' check (severity in ('LOW','MEDIUM','HIGH','CRITICAL')),
  status text not null default 'OPEN' check (status in ('OPEN','IN_REVIEW','RESOLVED','DISMISSED')),
  question text,
  analysis text,
  decision text,
  evidence jsonb not null default '[]'::jsonb,
  resolved_at timestamptz
);
create index if not exists idx_lgv_flags_open on public.lgv_research_flags(status, severity, opened_at desc);

create table if not exists public.lgv_shelf_snapshots (
  snapshot_date date not null,
  methodology_version text not null,
  asset_id uuid not null references public.lgv_assets(id) on delete cascade,
  shelf_floor smallint check (shelf_floor in (1,2)),
  opportunity_rank integer,
  is_top15 boolean not null default false,
  is_theoretical_portfolio boolean not null default false,
  price_status text,
  audit_grade char(1) not null default 'C' check (audit_grade in ('A','B','C')),
  created_at timestamptz not null default now(),
  primary key (snapshot_date, methodology_version, asset_id)
);
create index if not exists idx_lgv_snapshots_rank on public.lgv_shelf_snapshots(snapshot_date desc, opportunity_rank);

create table if not exists public.lgv_methodology_parameters (
  methodology_version text primary key,
  effective_from date not null,
  is_active boolean not null default false,
  parameters jsonb not null,
  notes text,
  created_at timestamptz not null default now()
);

-- Views leves para o motor e a interface.
create or replace view public.lgv_price_stats_annual with (security_invoker = true) as
select asset_id,
       extract(year from price_date)::int as year,
       avg(close)::numeric(20,8) as average_close,
       avg(financial_volume)::numeric(24,2) as average_financial_volume,
       count(*)::int as trading_days
from public.lgv_market_prices
group by asset_id, extract(year from price_date)::int;

create or replace view public.lgv_market_stats_12m with (security_invoker = true) as
with maxd as (select max(price_date) as max_date from public.lgv_market_prices)
select p.asset_id,
       avg(p.financial_volume)::numeric(24,2) as adtv_12m,
       count(*)::int as trading_days,
       max(p.price_date) as last_price_date
from public.lgv_market_prices p, maxd
where p.price_date > maxd.max_date - interval '365 days'
group by p.asset_id;

create or replace view public.lgv_dividend_stats_annual_raw with (security_invoker = true) as
select asset_id,
       extract(year from ex_date)::int as year,
       sum(amount_per_share)::numeric(20,10) as dpa_raw
from public.lgv_dividends
where asset_id is not null
group by asset_id, extract(year from ex_date)::int;

create or replace view public.lgv_latest_fy_net_income with (security_invoker = true) as
select distinct on (l.code_cvm)
       l.code_cvm,
       l.issuer_id,
       l.period_end,
       l.document_version,
       l.amount,
       l.scale,
       l.source
from public.lgv_cvm_financial_lines l
where l.document_type='DFP'
  and l.statement='DRE'
  and l.scope='CON'
  and l.account_code='3.11'
  and (upper(coalesce(l.exercise_order,'')) like '%ÚLTIM%' or upper(coalesce(l.exercise_order,'')) like '%ULTIM%')
order by l.code_cvm, l.period_end desc, l.document_version desc;

create or replace view public.lgv_treasury_reference_latest with (security_invoker = true) as
with latest as (
  select max(rate_date) as rate_date
  from public.lgv_treasury_rates
), candidates as (
  select t.*
  from public.lgv_treasury_rates t
  join latest l on l.rate_date=t.rate_date
  where t.buy_rate is not null
    and upper(t.title_type) like '%IPCA%'
    and upper(t.title_type) not like '%RENDA%'
    and upper(t.title_type) not like '%EDUCA%'
)
select
  rate_date,
  title_type,
  maturity_date,
  buy_rate,
  sell_rate,
  buy_price,
  sell_price,
  least(0.08::numeric, greatest(0.06::numeric, buy_rate + 0.005::numeric)) as lgv_required_yield,
  source,
  source_url
from candidates
order by maturity_date desc,
         case when upper(title_type) like '%JUROS%' then 1 else 0 end,
         title_type
limit 1;

create or replace view public.lgv_screener_latest with (security_invoker = true) as
select
  a.id as asset_id, a.ticker, a.company_name, a.display_name, a.sector,
  s.snapshot_date, s.methodology_version, s.adtv_12m, s.dy_5y, s.roe, s.roic,
  s.net_debt_ebitda, s.profit_positive, s.passes_liquidity, s.passes_dividend,
  s.passes_profit, s.passes_quality_reference, s.screening_status,
  s.fail_reasons, s.near_reasons, lp.close as market_price, lp.price_date as market_price_date
from public.lgv_assets a
join lateral (
  select ss.* from public.lgv_screening_snapshots ss
  where ss.asset_id=a.id order by ss.snapshot_date desc, ss.computed_at desc limit 1
) s on true
left join lateral (
  select p.close,p.price_date from public.lgv_market_prices p
  where p.asset_id=a.id order by p.price_date desc limit 1
) lp on true
where a.is_active=true and a.asset_class='ACAO';

create or replace view public.lgv_research_queue_latest with (security_invoker = true) as
select
  s.asset_id,
  s.ticker,
  s.company_name,
  s.display_name,
  s.sector,
  s.snapshot_date,
  s.methodology_version,
  s.screening_status,
  reason.value as reason,
  case reason.value
    when 'LUCRO_REPORTADO_NAO_POSITIVO_REQUER_AUDITORIA' then 'HIGH'
    when 'AJUSTE_EVENTO_SOCIETARIO_NECESSARIO' then 'HIGH'
    when 'HISTORICO_DY_INCOMPLETO' then 'MEDIUM'
    when 'LUCRO_ANUAL_PENDENTE' then 'MEDIUM'
    when 'LIQUIDEZ_PENDENTE' then 'MEDIUM'
    when 'DY_5A_ZONA_DE_APROXIMACAO' then 'LOW'
    when 'LIQUIDEZ_PROXIMA_AO_CORTE' then 'LOW'
    else 'MEDIUM'
  end as priority,
  case reason.value
    when 'LUCRO_REPORTADO_NAO_POSITIVO_REQUER_AUDITORIA' then 3
    when 'AJUSTE_EVENTO_SOCIETARIO_NECESSARIO' then 3
    when 'HISTORICO_DY_INCOMPLETO' then 2
    when 'LUCRO_ANUAL_PENDENTE' then 2
    when 'LIQUIDEZ_PENDENTE' then 2
    else 1
  end as priority_rank
from public.lgv_screener_latest s
cross join lateral jsonb_array_elements_text(coalesce(s.near_reasons, '[]'::jsonb)) as reason(value)
where s.screening_status in ('NEAR','PENDING');

create or replace view public.lgv_stock_dashboard_latest with (security_invoker = true) as
select
  a.id as asset_id,
  a.ticker,
  a.company_name,
  a.display_name,
  a.sector,
  ss.snapshot_date,
  ss.methodology_version,
  ss.shelf_floor,
  ss.opportunity_rank,
  ss.is_top15,
  ss.is_theoretical_portfolio,
  coalesce(v.audit_grade, ss.audit_grade, 'C') as audit_grade,
  coalesce(v.price_status, ss.price_status, 'PENDENTE') as price_status,
  v.quality_score,
  v.price_score,
  v.opportunity_score,
  v.pc_lgv,
  v.fair_value,
  v.income_ceiling,
  coalesce(v.market_price, lp.close) as market_price,
  lp.price_date as market_price_date,
  lp.source as market_source,
  v.source as valuation_source,
  ms.adtv_12m,
  coalesce(rf.open_research_flags,0) as open_research_flags
from public.lgv_assets a
join lateral (
  select s.* from public.lgv_shelf_snapshots s
  where s.asset_id=a.id
  order by s.snapshot_date desc, s.created_at desc
  limit 1
) ss on true
left join lateral (
  select vv.* from public.lgv_valuations vv
  where vv.asset_id=a.id
  order by vv.valuation_date desc, vv.computed_at desc
  limit 1
) v on true
left join lateral (
  select p.close, p.price_date, p.source from public.lgv_market_prices p
  where p.asset_id=a.id
  order by p.price_date desc
  limit 1
) lp on true
left join public.lgv_market_stats_12m ms on ms.asset_id=a.id
left join lateral (
  select count(*)::int as open_research_flags
  from public.lgv_research_flags f
  where f.asset_id=a.id and f.status in ('OPEN','IN_REVIEW')
) rf on true
where a.is_active=true;

-- Segurança: tabelas e views de research são somente server-side nesta fase.
do $$
declare r record;
begin
  for r in select tablename from pg_tables where schemaname='public' and tablename like 'lgv_%'
  loop
    execute format('alter table public.%I enable row level security', r.tablename);
    execute format('revoke all on table public.%I from anon, authenticated', r.tablename);
    execute format('grant all on table public.%I to service_role', r.tablename);
  end loop;
end $$;

revoke all on public.lgv_price_stats_annual from anon, authenticated;
revoke all on public.lgv_market_stats_12m from anon, authenticated;
revoke all on public.lgv_dividend_stats_annual_raw from anon, authenticated;
revoke all on public.lgv_latest_fy_net_income from anon, authenticated;
revoke all on public.lgv_treasury_reference_latest from anon, authenticated;
revoke all on public.lgv_screener_latest from anon, authenticated;
revoke all on public.lgv_research_queue_latest from anon, authenticated;
revoke all on public.lgv_stock_dashboard_latest from anon, authenticated;
grant select on public.lgv_price_stats_annual to service_role;
grant select on public.lgv_market_stats_12m to service_role;
grant select on public.lgv_dividend_stats_annual_raw to service_role;
grant select on public.lgv_latest_fy_net_income to service_role;
grant select on public.lgv_treasury_reference_latest to service_role;
grant select on public.lgv_screener_latest to service_role;
grant select on public.lgv_research_queue_latest to service_role;
grant select on public.lgv_stock_dashboard_latest to service_role;
