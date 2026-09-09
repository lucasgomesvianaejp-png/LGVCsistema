-- Snapshot estrutural legado v1.0, somente para bootstrap de interface.
-- NÃO libera compra: audit_grade=C e valuation permanece pendente.
with seed(ticker, display_name, sector, floor, rank, top15, portfolio) as (
 values
 ('BBSE3','BB Seguridade','Seguros e serviços financeiros',1,1,true,true),
 ('CMIG4','Cemig','Energia elétrica',1,2,true,true),
 ('LEVE3','Mahle Metal Leve','Autopeças',2,3,true,true),
 ('DIRR3','Direcional','Construção',1,4,true,true),
 ('LAVV3','Lavvi','Construção',2,5,true,true),
 ('BRSR6','Banrisul','Bancos',1,6,true,true),
 ('TGMA3','Tegma','Logística',1,7,true,true),
 ('CPFE3','CPFL Energia','Energia elétrica',1,8,true,false),
 ('WIZC3','Wiz Co','Serviços financeiros',1,9,true,false),
 ('ABCB4','Banco ABC Brasil','Bancos',1,10,true,true),
 ('JHSF3','JHSF','Construção',1,11,true,false),
 ('TIMS3','TIM','Telecomunicações',2,12,true,true),
 ('ITUB4','Itaú Unibanco','Bancos',1,13,true,false),
 ('BBDC3','Bradesco','Bancos',2,14,true,false),
 ('CYRE3','Cyrela','Construção',2,15,true,false),
 ('ITSA4','Itaúsa','Holdings financeiras',1,null,false,false),
 ('BMEB4','Banco Mercantil','Bancos',1,null,false,false),
 ('CXSE3','Caixa Seguridade','Seguros e serviços financeiros',1,null,false,false),
 ('KEPL3','Kepler Weber','Bens industriais',1,null,false,false),
 ('BMGB4','Banco BMG','Bancos',2,null,false,false),
 ('PETR4','Petrobras','Petróleo e gás',2,null,false,false),
 ('FIQE3','Unifique','Telecomunicações',2,null,false,false),
 ('FLRY3','Fleury','Saúde',2,null,false,false),
 ('CURY3','Cury','Construção',2,null,false,false)
), ins as (
 insert into public.lgv_assets(ticker, company_name, display_name, sector, asset_class)
 select ticker, display_name, display_name, sector, 'ACAO' from seed
 on conflict (ticker) do update set
   display_name=excluded.display_name,
   sector=coalesce(public.lgv_assets.sector, excluded.sector),
   updated_at=now()
 returning id, ticker
)
insert into public.lgv_shelf_snapshots(snapshot_date, methodology_version, asset_id, shelf_floor, opportunity_rank, is_top15, is_theoretical_portfolio, price_status, audit_grade)
select date '2026-09-09', 'v1.0-legacy-bootstrap', a.id, s.floor, s.rank, s.top15, s.portfolio, 'PENDENTE', 'C'
from seed s join public.lgv_assets a using (ticker)
on conflict (snapshot_date, methodology_version, asset_id) do update set
 shelf_floor=excluded.shelf_floor,
 opportunity_rank=excluded.opportunity_rank,
 is_top15=excluded.is_top15,
 is_theoretical_portfolio=excluded.is_theoretical_portfolio,
 price_status=excluded.price_status,
 audit_grade=excluded.audit_grade;
