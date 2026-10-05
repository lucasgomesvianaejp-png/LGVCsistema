# LGV Invest v4.5 — Relatório Investidor10 no formato cliente

Esta versão mantém o relatório MyProfit sem alterações e redesenha apenas o relatório cuja fonte é `Investidor10`.

## Objetivo

Aproximar o relatório Investidor10 do modelo histórico já enviado à cliente Alice, preservando a identidade visual da LGV Capital e utilizando apenas informações suportadas pela fonte.

## Estrutura do relatório Investidor10

1. Capa
2. Comentário do consultor
3. Resumo executivo
4. Distribuição da carteira — alocação atual vs. meta
5. Performance dos ativos e resumo consolidado

## Resumo executivo

O relatório prioriza quatro números simples:

- rentabilidade do período, quando o mês estiver fechado; em snapshot parcial, rentabilidade total acumulada;
- comparação com CDI quando disponível e aplicável; em snapshot parcial, ganho de capital;
- patrimônio;
- honorários LGV estimados pela taxa anual cadastrada no perfil (padrão 0,80% a.a.).

## Comentário

O fluxo existente de comentário foi mantido. O relatório Investidor10 agora inclui a página de comentário e aceita a mesma importação/edição de comentário usada nos demais relatórios.

## Alocação

A página mostra somente o que interessa ao cliente:

- distribuição por classe LGV;
- valor atual;
- peso atual;
- meta;
- leitura automática dos principais desvios.

Os motores continuam armazenados no JSON e no sistema, mas foram retirados do relatório cliente para reduzir excesso de informação.

## Ativos

A página de ativos segue a organização conhecida do Investidor10:

- Renda Fixa;
- Tesouro Direto;
- ETFs;
- Criptomoedas.

São exibidos rentabilidade do snapshot e valor atual, além de patrimônio total e ganho total acumulado.

## Snapshot parcial

Quando `isPartialSnapshot = true`, o relatório deixa explícito que a posição é parcial e não chama a variação patrimonial de rentabilidade mensal oficial.
