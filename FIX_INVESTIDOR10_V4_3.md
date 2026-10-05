# LGV Capital Sistema — v4.3 Investidor10 / dados indisponíveis

Esta revisão parte da v4.2 (replace exato por período) e corrige a renderização de snapshots mensais de fontes que não entregam o mesmo nível de detalhe do MyProfit, especialmente Investidor10.

## Correções principais

- `null`/`unavailable` não é mais convertido visualmente em `R$ 0,00` nos resultados mensais por classe e por motor.
- Motores preservam e exibem `currentWeight`, `targetWeight` e `differenceWeight` quando disponíveis.
- Resultado mensal por motor só é calculado quando há dado real; ausência de `assetResults` não fabrica zero.
- Ganho acumulado por posição/motor só aparece quando existem `gainValue` válidos.
- Cards de resumo deixam de mostrar zero para aportes, resgates e ganho financeiro quando a fonte não disponibiliza esses campos.
- `sourceGroupPerformance` passa a aparecer em bloco próprio como "Rentabilidade exibida no snapshot da fonte", sem ser rotulado como retorno mensal.
- O bloco de Resultado por Classe mostra "Não disponível na fonte" quando necessário, preservando alocação e alvo em página separada.
- A página de Dados e Premissas deixa de citar MyProfit de forma fixa e passa a identificar o provedor da fonte.
- Status de conciliação `acceptable_source_snapshot` e `source_snapshot_with_reservation` recebem rótulos próprios.
- Cabeçalho usa `positionFinalDate` quando disponível, distinguindo mês de referência da data de captura da posição.

## Regra estrutural mantida

Mesmo cliente + mesmo período continua substituindo integralmente o período importado, preservando os demais meses e os dados permanentes do perfil.
