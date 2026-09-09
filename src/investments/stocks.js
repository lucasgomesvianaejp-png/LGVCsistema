const SNAPSHOT_DATE = '09/09/2026';

// Snapshot estrutural importado da Política Geral de Ações v1.0.
// Valuation permanece propositalmente vazio até o LGV Engine estar conectado ao banco auditado.
const SEED = [
  ['BBSE3','BB Seguridade','Seguros e serviços financeiros','1º',1,true,true],
  ['CMIG4','Cemig','Energia elétrica','1º',2,true,true],
  ['LEVE3','Mahle Metal Leve','Autopeças','2º',3,true,true],
  ['DIRR3','Direcional','Construção','1º',4,true,true],
  ['LAVV3','Lavvi','Construção','2º',5,true,true],
  ['BRSR6','Banrisul','Bancos','1º',6,true,true],
  ['TGMA3','Tegma','Logística','1º',7,true,true],
  ['CPFE3','CPFL Energia','Energia elétrica','1º',8,true,false],
  ['WIZC3','Wiz Co','Serviços financeiros','1º',9,true,false],
  ['ABCB4','Banco ABC Brasil','Bancos','1º',10,true,true],
  ['JHSF3','JHSF','Construção','1º',11,true,false],
  ['TIMS3','TIM','Telecomunicações','2º',12,true,true],
  ['ITUB4','Itaú Unibanco','Bancos','1º',13,true,false],
  ['BBDC3','Bradesco','Bancos','2º',14,true,false],
  ['CYRE3','Cyrela','Construção','2º',15,true,false],
  ['ITSA4','Itaúsa','Holdings financeiras','1º',null,false,false],
  ['BMEB4','Banco Mercantil','Bancos','1º',null,false,false],
  ['CXSE3','Caixa Seguridade','Seguros e serviços financeiros','1º',null,false,false],
  ['KEPL3','Kepler Weber','Bens industriais','1º',null,false,false],
  ['BMGB4','Banco BMG','Bancos','2º',null,false,false],
  ['PETR4','Petrobras','Petróleo e gás','2º',null,false,false],
  ['FIQE3','Unifique','Telecomunicações','2º',null,false,false],
  ['FLRY3','Fleury','Saúde','2º',null,false,false],
  ['CURY3','Cury','Construção','2º',null,false,false]
].map(([ticker,company,sector,floor,rank,top15,portfolio]) => ({
  ticker, company, sector, floor, rank, top15, portfolio,
  auditGrade:'C', auditLabel:'Pendente', priceStatus:'Pendente',
  qualityScore:null, priceScore:null, opportunityScore:null,
  pcLgv:null, marketPrice:null, fairValue:null, incomeCeiling:null,
  source:'Snapshot LGV v1.0', snapshotDate:SNAPSHOT_DATE
}));

function money(value){
  return Number.isFinite(value) ? value.toLocaleString('pt-BR',{style:'currency',currency:'BRL'}) : '—';
}
function score(value){ return Number.isFinite(value) ? value.toFixed(2).replace('.',',') : '—'; }
function percent(value){ return Number.isFinite(value) ? (value*100).toFixed(2).replace('.',',')+'%' : '—'; }
function compactMoney(value){ return Number.isFinite(value) ? value.toLocaleString('pt-BR',{style:'currency',currency:'BRL',notation:'compact',maximumFractionDigits:1}) : '—'; }
function escapeHtml(value){ return String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;'); }

export function createStocksModule(root, options={}) {
  let stocks = [...SEED];
  let activeTab = 'shelf';
  let search = '';
  let detailTicker = '';
  let meta = { universeCount: null, databaseMode: false, ingestion: [] };
  let screener = [];
  let researchQueue = [];
  const onStatus = options.onStatus || (()=>{});

  async function load(){
    onStatus('Carregando módulo de ações…','warn');
    try {
      if (options.dataProvider) {
        const live = await options.dataProvider();
        if (Array.isArray(live) && live.length) { stocks = live; meta.databaseMode = true; }
        else if (live && Array.isArray(live.stocks)) {
          if (live.stocks.length) stocks = live.stocks;
          meta = { ...meta, ...(live.meta || {}), databaseMode: true };
          if (Array.isArray(live.screener)) screener = live.screener;
          if (Array.isArray(live.researchQueue)) researchQueue = live.researchQueue;
        }
      }
      onStatus('Ações carregadas','ok');
    } catch (error) {
      console.warn('[LGV Ações] Falha ao carregar backend; usando snapshot local.', error);
      onStatus('Estante em modo local','warn');
    }
    render();
  }

  function selected(){
    let list = activeTab === 'screener' && screener.length ? screener : (activeTab === 'research' && researchQueue.length ? researchQueue : stocks);
    if (activeTab === 'top15') list = list.filter(x=>x.top15);
    if (activeTab === 'portfolio') list = list.filter(x=>x.portfolio);
    if (activeTab === 'research' && !researchQueue.length) list = list.filter(x=>x.auditGrade !== 'A');
    if (search) {
      const q = search.toLocaleLowerCase('pt-BR');
      list = list.filter(x=>`${x.ticker} ${x.company} ${x.sector || ''} ${x.floor || ''}`.toLocaleLowerCase('pt-BR').includes(q));
    }
    return list;
  }

  function renderStats(){
    root.querySelector('[data-stock-stat="universe"]').textContent = Number.isFinite(meta.universeCount) ? meta.universeCount : stocks.length;
    root.querySelector('[data-stock-stat="shelf"]').textContent = stocks.length;
    root.querySelector('[data-stock-stat="top15"]').textContent = stocks.filter(x=>x.top15).length;
    root.querySelector('[data-stock-stat="portfolio"]').textContent = stocks.filter(x=>x.portfolio).length;
    root.querySelector('[data-stock-stat="buy"]').textContent = stocks.filter(x=>x.priceStatus==='Compra' && x.auditGrade==='A').length;
    root.querySelector('[data-stock-stat="research"]').textContent = researchQueue.length || stocks.filter(x=>x.auditGrade!=='A').length;
  }

  function renderTable(){
    const list = selected();
    const tbody = root.querySelector('[data-stocks-body]');
    const head = root.querySelector('[data-stock-head]');
    if (activeTab === 'research' && researchQueue.length) {
      head.innerHTML = '<th>Ativo</th><th>Setor</th><th>Prioridade</th><th>Pendência objetiva</th><th>Snapshot</th>';
      tbody.innerHTML = list.map(x=>{
        const badge = x.priority==='HIGH' ? 'audit-c' : x.priority==='LOW' ? 'audit-a' : 'pending';
        return `<tr>
          <td><div class="stock-ticker">${escapeHtml(x.ticker)}</div><div class="stock-company">${escapeHtml(x.company)}</div></td>
          <td>${escapeHtml(x.sector)}</td>
          <td><span class="stock-badge ${badge}">${escapeHtml(x.priority)}</span></td>
          <td class="stock-company">${escapeHtml(x.reason)}</td>
          <td>${escapeHtml(x.snapshotDate || '—')}</td>
        </tr>`;
      }).join('') || '<tr><td colspan="5" style="text-align:center;color:#7c8796;padding:28px">Nenhuma pendência automática.</td></tr>';
      return;
    }
    if (activeTab === 'screener' && screener.length) {
      head.innerHTML = '<th>Ativo</th><th>Setor</th><th>Liquidez 12M</th><th>DY bruto 5A</th><th>Lucro</th><th>Cotação</th><th>Status</th><th>Motivo / próximo passo</th>';
      tbody.innerHTML = list.map(x=>{
        const reasons = [...(x.failReasons||[]), ...(x.nearReasons||[])];
        const label = ({PASS:'Passou pré-filtro',NEAR:'Aproximação',FAIL:'Fora',PENDING:'Pendente'})[x.status] || x.status;
        const badge = x.status==='PASS' ? 'audit-a' : x.status==='FAIL' ? 'audit-c' : 'pending';
        return `<tr>
          <td><div class="stock-ticker">${escapeHtml(x.ticker)}</div><div class="stock-company">${escapeHtml(x.company)}</div></td>
          <td>${escapeHtml(x.sector)}</td>
          <td>${compactMoney(x.adtv12m)}</td>
          <td>${percent(x.dy5y)}</td>
          <td>${x.profitPositive===true?'Positivo':x.profitPositive===false?'Revisar':'—'}</td>
          <td>${money(x.marketPrice)}</td>
          <td><span class="stock-badge ${badge}">${escapeHtml(label)}</span></td>
          <td class="stock-company">${escapeHtml(reasons.join(' · ') || 'Elegível para próxima etapa quantitativa')}</td>
        </tr>`;
      }).join('') || '<tr><td colspan="8" style="text-align:center;color:#7c8796;padding:28px">Screener ainda não calculado.</td></tr>';
      return;
    }
    head.innerHTML = '<th>Ativo</th><th>Setor</th><th>Andar</th><th>Ranking</th><th>Qualidade</th><th>Oportunidade</th><th>PC LGV</th><th>Cotação</th><th>Status</th><th>Auditoria</th>';
    tbody.innerHTML = list.map(x=>`
      <tr data-stock-open="${escapeHtml(x.ticker)}">
        <td><div class="stock-ticker">${escapeHtml(x.ticker)}</div><div class="stock-company">${escapeHtml(x.company)}</div></td>
        <td>${escapeHtml(x.sector)}</td>
        <td><span class="stock-badge ${x.floor==='1º'?'floor1':'floor2'}">${escapeHtml(x.floor)} andar</span></td>
        <td>${x.rank ? `#${x.rank}` : '<span class="stock-empty-value">—</span>'}</td>
        <td>${score(x.qualityScore)}</td>
        <td>${score(x.opportunityScore)}</td>
        <td>${money(x.pcLgv)}</td>
        <td>${money(x.marketPrice)}</td>
        <td><span class="stock-badge pending">${escapeHtml(x.priceStatus)}</span></td>
        <td><span class="stock-badge audit-${String(x.auditGrade).toLowerCase()}">Grau ${escapeHtml(x.auditGrade)}</span></td>
      </tr>`).join('') || '<tr><td colspan="10" style="text-align:center;color:#7c8796;padding:28px">Nenhum ativo neste filtro.</td></tr>';
  }

  function renderDetail(){
    const stock = stocks.find(x=>x.ticker===detailTicker);
    const listView = root.querySelector('[data-stock-list-view]');
    const detail = root.querySelector('[data-stock-detail]');
    if (!stock) { listView.classList.remove('hidden'); detail.classList.remove('active'); return; }
    listView.classList.add('hidden'); detail.classList.add('active');
    root.querySelector('[data-detail-ticker]').textContent = stock.ticker;
    root.querySelector('[data-detail-company]').textContent = `${stock.company} · ${stock.sector}`;
    root.querySelector('[data-detail-floor]').textContent = `${stock.floor} andar`;
    root.querySelector('[data-detail-rank]').textContent = stock.rank ? `#${stock.rank}` : '—';
    root.querySelector('[data-detail-audit]').textContent = `Grau ${stock.auditGrade}`;
    root.querySelector('[data-detail-status]').textContent = stock.priceStatus;
    root.querySelector('[data-detail-price]').textContent = money(stock.marketPrice);
    root.querySelector('[data-detail-pc]').textContent = money(stock.pcLgv);
    root.querySelector('[data-detail-fair]').textContent = money(stock.fairValue);
    root.querySelector('[data-detail-income]').textContent = money(stock.incomeCeiling);
    root.querySelector('[data-detail-quality]').textContent = score(stock.qualityScore);
    root.querySelector('[data-detail-price-score]').textContent = score(stock.priceScore);
    root.querySelector('[data-detail-opportunity]').textContent = score(stock.opportunityScore);
    root.querySelector('[data-detail-source]').textContent = stock.source || '—';
    root.querySelector('[data-detail-snapshot]').textContent = stock.snapshotDate || '—';
    root.querySelector('[data-detail-portfolio]').textContent = stock.portfolio ? 'Sim' : 'Não';
    root.querySelector('[data-detail-top15]').textContent = stock.top15 ? 'Sim' : 'Não';
  }

  function renderDataStatus(){
    const box = root.querySelector('[data-stock-data-status]');
    if (!box) return;
    if (!meta.databaseMode) {
      box.innerHTML = '<span class="stock-dot warn"></span><strong>Modo local:</strong> backend de research indisponível; exibindo snapshot estrutural sem liberar ordens.';
      return;
    }
    const ok = (meta.ingestion || []).filter(x=>x.status==='SUCCESS');
    const last = ok[0];
    const when = last?.finished_at ? new Date(last.finished_at).toLocaleString('pt-BR') : 'sem ingestão registrada';
    box.innerHTML = `<span class="stock-dot ok"></span><strong>LGV Research DB conectado.</strong> Última ingestão concluída: ${escapeHtml(when)}. Valuation só é liberado quando o ativo atingir o grau de auditoria exigido.`;
  }

  function render(){
    renderStats();
    renderDataStatus();
    root.querySelectorAll('[data-stock-tab]').forEach(btn=>btn.classList.toggle('active',btn.dataset.stockTab===activeTab));
    root.querySelector('[data-stock-table-title]').textContent = ({shelf:'Estante LGV',screener:'Screener',top15:'Top 15',portfolio:'Carteira teórica',research:'Research pendente'})[activeTab] || 'Estante LGV';
    renderTable();
    renderDetail();
  }

  root.addEventListener('click', event=>{
    const tab = event.target.closest('[data-stock-tab]')?.dataset.stockTab;
    if (tab) { activeTab=tab; detailTicker=''; render(); return; }
    const ticker = event.target.closest('[data-stock-open]')?.dataset.stockOpen;
    if (ticker) { detailTicker=ticker; renderDetail(); return; }
    if (event.target.closest('[data-stock-back]')) { detailTicker=''; renderDetail(); return; }
  });
  root.querySelector('[data-stock-search]')?.addEventListener('input', event=>{ search=event.target.value.trim(); renderTable(); });
  root.querySelector('[data-stock-refresh]')?.addEventListener('click', ()=>load());

  return { load, render, getStocks:()=>[...stocks], getMeta:()=>({...meta}) };
}
