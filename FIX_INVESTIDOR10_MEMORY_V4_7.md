# LGV Capital Sistema v4.7 — memória Investidor10

## Objetivo

Transformar os snapshots mensais do Investidor10 em uma base histórica própria da LGV, sem alterar o relatório MyProfit.

## 1. Mês analisado x snapshot

Um JSON capturado em 05/11 pode representar a análise de outubro. O sistema mantém dois conceitos:

- `analysisPeriod`: mês analisado;
- `snapshotDate`: data em que a posição foi capturada.

O seletor mostra o mês analisado. A data do snapshot aparece como informação auxiliar.

## 2. Memória persistente

Cada importação Investidor10 cria/atualiza uma entrada em:

```json
"investidor10Memory": {
  "snapshots": {
    "2026-10-05": { "...": "..." },
    "2026-11-05": { "...": "..." }
  },
  "externalFlows": []
}
```

Reimportar a mesma data substitui somente aquele snapshot. Importar uma nova data adiciona histórico.

## 3. Aportes e resgates

O JSON pode informar fluxos externos no bloco `externalFlows`.

Campos mínimos:

- `date`;
- `type`: `aporte` / `resgate` (ou `contribution` / `withdrawal`);
- `value`;
- `assetId` quando o dinheiro puder ser associado a um ativo.

Quando o ativo estiver cadastrado, o sistema completa `classLGV` e `strategicFunction` automaticamente.

Compras e vendas comuns de ativos **não são tratadas como fluxo externo**. Só entram na memória de fluxos quando vierem explicitamente como aporte/resgate.

## 4. Cálculo entre snapshots

Com dois snapshots completos e os fluxos externos do intervalo, o sistema calcula:

- resultado financeiro líquido de aportes/resgates;
- retorno estimado entre snapshots por Modified Dietz;
- a mesma lógica por classe LGV e motor, quando as duas fotografias contiverem esses blocos e os fluxos estiverem classificados.

A rentabilidade oficial do Investidor10, quando disponível, continua sendo a fonte primária. O cálculo LGV é fallback e aparece identificado como estimativa.

## 5. Comentário

O comentário pode ser vinculado a `analysisPeriod`, mesmo quando o snapshot pertence ao mês seguinte. Ele é salvo em `consultantComments[AAAA-MM]`, evitando criar um mês vazio apenas para guardar texto.

## 6. Leitura da alocação

O bloco voltou a ser uma leitura textual do portfólio, em dois parágrafos. A tabela continua mostrando Atual x Meta, mas a interpretação passa a destacar somente:

- posição de Renda Fixa versus meta;
- classes acima/abaixo da meta com desvio relevante;
- prioridades para os próximos aportes;
- ausência de necessidade de grandes movimentações quando aplicável.
