# LGV Research — Pipeline de dados

## Objetivo

Evitar que cada atualização da Estante reconstrua 300+ empresas por pesquisa aberta. O sistema mantém um banco incremental e só envia para research profundo os casos que realmente exigem julgamento.

## Fontes automatizadas

### B3 — COTAHIST

- URL anual: `https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{AAAA}.ZIP`
- Parser de largura fixa seguindo o layout oficial COTAHIST.
- Mercado usado para preço econômico: `TPMERC=010`.
- Grava preços, negócios, quantidade, volume, ISIN, espécie e fator de cotação.
- O arquivo anual corrente é reprocessável: `upsert` impede duplicação por `(asset_id, price_date)`.

### B3 — Empresas Listadas

- `GetInitialCompanies`: catálogo de emissores e `codeCVM`.
- `GetListedSupplementCompany`: metadados, proventos em dinheiro e eventos societários.
- O vínculo com a CVM é por `codeCVM`; o vínculo entre provento e ação é pelo ISIN.
- Não há fuzzy match por nome no fluxo normal.

### CVM — DFP / ITR

- Arquivos ZIP anuais oficiais.
- O pipeline não replica a CVM inteira: guarda somente contas que a metodologia LGV pode usar.
- Mantém versão, período, escopo consolidado/individual, código e descrição da conta para auditoria.
- Reapresentações não apagam o histórico de versões.

### Tesouro Transparente

- CSV oficial de Taxas dos Títulos Ofertados pelo Tesouro Direto.
- Mantém série diária de taxa/PU por título e vencimento.
- Taxas percentuais são normalizadas para formato decimal no banco (`7,30%` -> `0.073`).

## Cadência

### Diária, após pregão

1. COTAHIST do ano corrente.
2. Taxas do Tesouro.
3. Pré-screening quantitativo.

### Semanal

1. Catálogo B3.
2. Suplemento B3 (dividendos e eventos societários).
3. ITR do ano corrente.
4. DFP dos cinco exercícios completos.
5. Pré-screening novamente.

## Funil barato

O pré-screen não tenta fazer valuation nem substituir a auditoria LGV.

Ele pode eliminar automaticamente apenas quando a conclusão é forte:

- liquidez média de 12 meses abaixo do mínimo;
- DY bruto de cinco exercícios claramente abaixo da régua, desde que não exista evento societário que exija ajuste;
- setores já estruturalmente excluídos quando a classificação estiver disponível.

Zona de aproximação:

- DY bruto entre 5,5% e 6,0%;
- liquidez entre R$ 1,0 e R$ 1,2 milhão/dia;
- lucro reportado não positivo;
- histórico incompleto;
- desdobramento/bonificação no período.

A zona de aproximação existe para não perder oportunidade sem obrigar research completo sobre todo o universo.

## O que ainda exige research

- classificar dividendos recorrentes x extraordinários;
- normalizar lucro materialmente afetado por eventos não recorrentes;
- avaliar qualidade de caixa, dívida e previsibilidade;
- fechar Nota de Qualidade final;
- resolver flags contábeis/regulatórias;
- emitir Grau de Auditoria final.

## Segurança

O navegador nunca lê Supabase com `service_role`.

Fluxo:

`Firebase login -> /api/research/* -> valida ID token -> Supabase service_role no servidor`.

As tabelas `lgv_*` têm RLS habilitada e acesso de `anon/authenticated` revogado nesta fase.

## Fila automática de research

A view `lgv_research_queue_latest` transforma os motivos `NEAR/PENDING` do screener em tarefas objetivas e priorizadas.

Prioridade alta inclui, por exemplo:

- lucro reportado não positivo que exige auditoria de recorrência;
- evento societário que impede eliminação automática pelo DY.

Assim, a IA ou o analista recebe uma pergunta específica em vez de reanalisar o universo inteiro.

## Referência do Tesouro

A view `lgv_treasury_reference_latest` seleciona o último dia disponível, títulos tradicionais indexados ao IPCA, o vencimento mais longo e calcula `DY_exigido_LGV = min(8%, max(6%, taxa_compra + 0,5 p.p.))`. Em empate de vencimento, prefere o título sem cupom semestral.
