# LGV Invest v4.4 — Relatórios por fonte

Esta versão preserva integralmente o renderizador existente para relatórios MyProfit e adiciona um renderizador dedicado para snapshots do Investidor10.

## Regra de seleção

- `report.source.provider = "Investidor10"` -> relatório específico Investidor10.
- Demais fontes -> relatório legado/MyProfit sem alteração de lógica.

## Relatório Investidor10

O relatório não exige resultado mensal por classe ou por motor. Em vez disso, aproveita os dados que a fonte realmente disponibiliza:

- patrimônio, valor aplicado, ganho de capital e rentabilidade acumulada;
- evolução patrimonial capturada da fonte;
- valores, pesos, alvos, diferenças em R$ e p.p. por classe LGV;
- valores, pesos, alvos, diferenças em R$ e p.p. por motor LGV;
- variação acumulada sobre custo visível, calculada a partir dos lotes de compra quando disponíveis;
- rentabilidade e variação exibidas pelo Investidor10 por grupo e por ativo;
- posições completas.

Os cartões de grupo do Investidor10 são tratados como autoridade para valor consolidado. Quando linhas individuais não fecham exatamente com o cartão do grupo em um snapshot ao vivo, a consolidação LGV reconcilia proporcionalmente apenas para fins de soma por classe/motor, preservando o valor bruto em `sourceMarketValue`.

## Setembro x outubro

O snapshot de 05/10/2026 é tratado como outubro parcial e não substitui setembro. O fechamento patrimonial exibido no gráfico para 09/26 permanece como ponto histórico separado.
