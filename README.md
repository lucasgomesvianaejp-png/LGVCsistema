# LGV Capital Sistema — Firebase Research Layer v3

Esta versão preserva Clientes/Relatórios e adiciona a infraestrutura institucional de ações usando **o mesmo Firebase `lvg-invest`**.

## O que mudou
- Supabase removido.
- `Investimentos > Ações` lê o Firestore existente.
- GitHub Actions atualiza B3/CVM/Tesouro via Firebase Admin.
- Dados financeiros são armazenados de forma agregada para reduzir custo.
- Pré-screen `PASS / NEAR / FAIL / PENDING` reduz o universo antes de research profundo.
- `researchDashboard/current` concentra a visão principal e reduz leituras no navegador.
- Firebase Hosting incluído para hospedagem estática.

## O que continua igual
- Firebase Auth existente.
- `clients` e `clientData`.
- fluxo atual de relatórios/PDF.

## Primeiro uso
Leia `docs/DEPLOYMENT_FIREBASE.md`.

### Sequência
1. Adicionar o Secret `FIREBASE_SERVICE_ACCOUNT_LGV_INVEST` no GitHub.
2. Mesclar o trecho de regras `firebase/firestore-research.rules.snippet` às regras atuais.
3. GitHub Actions -> **LGV Research Bootstrap** -> Run workflow.
4. Abrir `Investimentos > Ações`.

## Testes
```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts engine
node --check src/investments/research-api.js
node --check src/investments/stocks.js
```

## Atualização — Dashboard de Clientes e Observações

Esta versão adiciona ao módulo de clientes:

- Dashboard inicial com AUM consolidado da base ativa.
- Honorários estimados mensais e anuais.
  - Taxa padrão: 0,80% a.a. quando o cliente ainda não possui taxa própria cadastrada.
  - A taxa pode ser editada em Perfil e estratégia > Honorários (% a.a.).
- Lista de aniversariantes do mês, usando a data de nascimento do perfil.
- Tabela consolidada de clientes com AUM, taxa e honorários mensais estimados.
- Nova aba Observações no perfil do cliente.
  - Cada observação possui título e informação.
  - É possível adicionar, editar e excluir itens.
  - Os itens são gravados em `clients/{clientId}/observations/{observationId}` e não aumentam o documento principal do cliente.

### Regra Firestore das observações

Se as regras atuais do Firestore não permitirem subcoleções de `clients`, mescle o conteúdo de:

`firebase/firestore-client-observations.rules.snippet`

Não substitua as regras atuais inteiras apenas por esse trecho.

## Atualização v4.2 — Importação JSON por substituição de período

A importação mensal agora segue a regra:

- mesmo `clientId` + mesmo `period` = substituição integral dos dados daquele período;
- mesmo `clientId` + período novo = inclusão de novo período.

Na substituição de um período, o sistema preserva cadastro, observações manuais e demais meses, mas troca de forma autoritativa os blocos do mês importado, incluindo `reportSnapshots[period]`, desempenho mensal/diário do período, posições do fechamento, caixa/proventos vinculados ao ciclo, planos/status indexados pelo período e outros arrays/mapas com marca temporal explícita.

Após a gravação, o workspace continua usando a versão recém-importada em memória — não refaz merge com dados antigos — e seleciona imediatamente o período importado para relatório/PDF.

Mensagem visual:

- `Período AAAA-MM atualizado com sucesso.` quando o mês já existia;
- `Período AAAA-MM adicionado com sucesso.` quando é um mês novo.


## v4.5 — relatório Investidor10 no formato cliente

O relatório de fonte Investidor10 foi simplificado para o padrão de comunicação já utilizado com clientes: capa, comentário, resumo executivo, distribuição da carteira e performance dos ativos. O relatório MyProfit permanece preservado. Veja `FIX_INVESTIDOR10_CLIENT_REPORT_V4_5.md`.

## v4.6 — mês fechado + posição atual no Investidor10

Quando o JSON do Investidor10 é um snapshot parcial do mês corrente, o relatório passa a analisar automaticamente o último mês fechado. Exemplo: snapshot de 05/10/2026 gera relatório de setembro/2026, preservando 05/10/2026 apenas como data-base da posição atual.

Principais ajustes:
- capa, cabeçalhos e comentário vinculados ao último mês fechado;
- rentabilidade mensal retirada de `monthlyPerformance`;
- patrimônio, ganho acumulado e ganho de capital do mês retirados do histórico patrimonial do Investidor10;
- alocação atual x meta usa a posição mais recente, com layout simplificado;
- resumo consolidado mostra patrimônio de fechamento, ganho no mês e ganho total acumulado;
- rentabilidades por ativo continuam identificadas como dados do snapshot atual;
- CDI/IPCA, quando atualizados, usam o mês analisado e não o mês parcial do snapshot.

Veja `FIX_INVESTIDOR10_MONTH_CLOSE_V4_6.md`.

## v4.7 — memória de snapshots, fluxos e seletor por mês analisado (Investidor10)

O fluxo Investidor10 agora separa definitivamente **mês analisado** de **data do snapshot**.

- O seletor exibe o mês analisado (ex.: `setembro de 2026`).
- A data-base aparece logo abaixo como `Snapshot da carteira: 05/10/2026`.
- Cada importação Investidor10 passa a alimentar `investidor10Memory.snapshots`, preservando a fotografia completa por data.
- A memória anterior é migrada automaticamente a partir do último snapshot já salvo antes de incorporar o novo JSON.
- O JSON pode trazer `externalFlows` com aportes/resgates. Basta informar data, tipo, valor e ativo; classe LGV e motor são preenchidos pelo cadastro de ativos quando disponíveis.
- Aportes/resgates são persistidos sem duplicação em `investidor10Memory.externalFlows`.
- Quando houver dois snapshots completos, o sistema calcula internamente o resultado líquido de fluxos e uma taxa estimada por **Modified Dietz**, inclusive por classe e motor quando houver dados suficientes.
- A rentabilidade oficial da fonte continua tendo prioridade quando existir. O cálculo entre snapshots só é usado como fallback e é identificado como estimativa LGV.
- Comentários do Investidor10 podem ser gravados pelo mês analisado sem criar um falso mês de relatório no seletor.
- A leitura da alocação voltou a ser texto corrido em dois parágrafos, com destaque apenas para desvios relevantes e prioridades de novos aportes.

Veja `FIX_INVESTIDOR10_MEMORY_V4_7.md` e `EXEMPLO_FLUXOS_INVESTIDOR10.json`.
