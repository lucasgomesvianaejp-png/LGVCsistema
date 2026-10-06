# v4.6 — Investidor10: relatório do mês fechado com posição atual

Problema resolvido: um snapshot capturado no início de outubro estava gerando um relatório rotulado como outubro, apesar de a análise mensal correta ser setembro.

## Regra nova

- Se o snapshot estiver marcado como parcial, o relatório analisa o mês imediatamente anterior.
- O fechamento mensal vem do `equityHistory` do Investidor10.
- A rentabilidade mensal vem de `monthlyPerformance`.
- A posição dos ativos e a alocação continuam usando o snapshot mais recente e são claramente datadas.

## Exemplo Alice — setembro/2026

- Rentabilidade oficial do mês: 1,06%.
- Patrimônio no fechamento de setembro: R$ 80.221,05.
- Ganho de capital acumulado no fechamento: R$ 7.223,04.
- Ganho de capital no mês: R$ 1.090,72, calculado pela diferença entre o ganho acumulado de setembro e agosto.
- Posição atual usada para alocação e ativos: snapshot de 05/10/2026.

A variação do ganho de capital não é rotulada como rentabilidade mensal; a rentabilidade oficial permanece a informada pelo Investidor10.

## Comentário do consultor

O relatório Investidor10 passa a procurar primeiro o comentário do mês analisado (setembro, no exemplo) e, se não existir, usa o comentário vinculado ao snapshot atual.

## Layout

A página de alocação foi simplificada para Categoria / Atual / Meta, mais próxima do relatório histórico do cliente. O resumo consolidado da página de ativos agora mostra patrimônio de fechamento, ganho no mês e ganho total acumulado.
