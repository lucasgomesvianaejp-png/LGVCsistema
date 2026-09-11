#!/usr/bin/env python3
from __future__ import annotations
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from lgv_data.common import FirestoreRepo,utc_now_iso

SEED=[
('BBSE3','BB Seguridade','Seguros e serviços financeiros','1º',1,True,True),('CMIG4','Cemig','Energia elétrica','1º',2,True,True),('LEVE3','Mahle Metal Leve','Autopeças','2º',3,True,True),
('DIRR3','Direcional','Construção','1º',4,True,True),('LAVV3','Lavvi','Construção','2º',5,True,True),('BRSR6','Banrisul','Bancos','1º',6,True,True),('TGMA3','Tegma','Logística','1º',7,True,True),
('CPFE3','CPFL Energia','Energia elétrica','1º',8,True,False),('WIZC3','Wiz Co','Serviços financeiros','1º',9,True,False),('ABCB4','Banco ABC Brasil','Bancos','1º',10,True,True),('JHSF3','JHSF','Construção','1º',11,True,False),
('TIMS3','TIM','Telecomunicações','2º',12,True,True),('ITUB4','Itaú Unibanco','Bancos','1º',13,True,False),('BBDC3','Bradesco','Bancos','2º',14,True,False),('CYRE3','Cyrela','Construção','2º',15,True,False),
('ITSA4','Itaúsa','Holdings financeiras','1º',None,False,False),('BMEB4','Banco Mercantil','Bancos','1º',None,False,False),('CXSE3','Caixa Seguridade','Seguros e serviços financeiros','1º',None,False,False),
('KEPL3','Kepler Weber','Bens industriais','1º',None,False,False),('BMGB4','Banco BMG','Bancos','2º',None,False,False),('PETR4','Petrobras','Petróleo e gás','2º',None,False,False),('FIQE3','Unifique','Telecomunicações','2º',None,False,False),
('FLRY3','Fleury','Saúde','2º',None,False,False),('CURY3','Cury','Construção','2º',None,False,False)]

def main():
    db=FirestoreRepo(); assets={x['id']:x for x in db.all('researchAssets')}; market={x['id']:x for x in db.all('researchMarket')}; valuations=(db.get('researchValuations','current') or {}).get('items') or []
    valmap={x.get('ticker'):x for x in valuations}; stocks=[]
    for ticker,company,sector,floor,rank,top15,portfolio in SEED:
        a=assets.get(ticker,{}) or {}; m=market.get(ticker,{}) or {}; v=valmap.get(ticker,{}) or {}
        stocks.append({'ticker':ticker,'company':a.get('companyName') or company,'sector':a.get('sector') or sector,'floor':floor,'rank':rank,'top15':top15,'portfolio':portfolio,
            'auditGrade':v.get('auditGrade','C'),'auditLabel':v.get('auditLabel','Pendente'),'priceStatus':v.get('priceStatus','Pendente'),
            'qualityScore':v.get('qualityScore'),'priceScore':v.get('priceScore'),'opportunityScore':v.get('opportunityScore'),'pcLgv':v.get('pcLgv'),'marketPrice':m.get('lastPrice'),
            'fairValue':v.get('fairValue'),'incomeCeiling':v.get('incomeCeiling'),'source':v.get('source','Firebase LGV Research'),'snapshotDate':v.get('snapshotDate') or m.get('lastPriceDate')})
    screen=db.get('researchScreening','current') or {}; screener=screen.get('items') or []
    queue=[]
    for x in screener:
        reasons=list(x.get('failReasons') or [])+list(x.get('nearReasons') or [])
        if x.get('status') in {'NEAR','PENDING'} or any('AUDITORIA' in r or 'AJUSTE' in r for r in reasons):
            priority='HIGH' if any('AJUSTE' in r or 'AUDITORIA' in r for r in reasons) else 'LOW'
            queue.append({'ticker':x['ticker'],'company':x.get('company') or x['ticker'],'sector':x.get('sector') or '','priority':priority,'reason':' · '.join(reasons) or 'Revisão necessária','snapshotDate':screen.get('snapshotDate')})
    runs=sorted(db.all('researchIngestionRuns'),key=lambda x:x.get('finishedAt') or x.get('startedAt') or '',reverse=True)[:8]
    payload={'stocks':stocks,'screener':screener,'researchQueue':queue,'meta':{'universeCount':len(screener) or len(assets),'databaseMode':True,'ingestion':runs,
        'screeningCounts':screen.get('counts') or {},'screeningDate':screen.get('snapshotDate'),'updatedAt':utc_now_iso(),'storageModel':'FIRESTORE_AGGREGATED'}}
    db.set('researchDashboard','current',payload,merge=False)
    print(f'Dashboard atualizado: {len(stocks)} estante, {len(screener)} screener, {len(queue)} research.')
if __name__=='__main__': main()
