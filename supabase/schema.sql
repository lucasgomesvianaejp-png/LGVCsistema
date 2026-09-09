-- LGV Capital Research — schema inicial
-- Projetado para acesso apenas por backend confiável/service role nesta fase.
-- O frontend atual continua autenticado pelo Firebase e NÃO recebe service_role.

create extension if not exists pgcrypto;

create table if not exists public.lgv_assets (
  id uuid primary key default gen_random_uuid(),
  ticker text not null unique,
  company_name text not null,
  cnpj text,
  asset_class text not null default 'ACAO',
  sector text,
  subsector text,
  share_class text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.lgv_market_prices (
  asset_id uuid not null references public.lgv_assets(id) on delete cascade,
  price_date date not null,
  close numeric(20,8) not null,
  financial_volume numeric(24,2),
  source text not null,
  source_grade char(1) not null default 'C' check (source_grade in ('A','B','C','D')),
  ingested_at timestamptz not null default now(),
  primary key (asset_id, price_date)
);

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
  diluted_shares numeric(24,4),
  source text not null,
  source_grade char(1) not null default 'C' check (source_grade in ('A','B','C','D')),
  ingested_at timestamptz not null default now(),
  unique (asset_id, period_end, period_type)
);

create table if not exists public.lgv_dividends (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.lgv_assets(id) on delete cascade,
  ex_date date not null,
  payment_date date,
  event_type text not null,
  amount_per_share numeric(20,8) not null,
  recurrence_class text not null default 'PENDING' check (recurrence_class in ('RECURRING','EXTRAORDINARY','UNCERTAIN','PENDING')),
  source text not null,
  source_grade char(1) not null default 'C' check (source_grade in ('A','B','C','D')),
  research_note text,
  unique (asset_id, ex_date, event_type, amount_per_share)
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
  dpa_5y numeric(20,8),
  payout_sustainable numeric(12,6),
  dpa_fundamental numeric(20,8),
  dpa_lgv numeric(20,8),
  audit_grade char(1) not null default 'C' check (audit_grade in ('A','B','C')),
  methodology_version text not null,
  computed_at timestamptz not null default now(),
  primary key (asset_id, metric_date, methodology_version)
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

create index if not exists idx_lgv_prices_asset_date on public.lgv_market_prices(asset_id, price_date desc);
create index if not exists idx_lgv_financials_asset_period on public.lgv_financial_periods(asset_id, period_end desc);
create index if not exists idx_lgv_dividends_asset_ex on public.lgv_dividends(asset_id, ex_date desc);
create index if not exists idx_lgv_flags_open on public.lgv_research_flags(status, severity, opened_at desc);
create index if not exists idx_lgv_snapshots_rank on public.lgv_shelf_snapshots(snapshot_date desc, opportunity_rank);

-- Segurança: nenhuma destas tabelas deve ser acessada diretamente pelo navegador nesta fase.
-- O Firebase continua como autenticação do app; a futura API server-side fará a ponte.
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
