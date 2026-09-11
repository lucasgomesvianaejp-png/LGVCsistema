# LGV Research — Data Pipeline

## Bootstrap
`B3 catálogo -> COTAHIST 5 anos + ano corrente -> suplementos B3 -> DFP 5 exercícios -> ITR corrente -> Tesouro -> pré-screen -> researchDashboard/current`

## Diário
`COTAHIST ano anterior + corrente -> ADTV 12M/preço -> Tesouro -> pré-screen -> dashboard`

## Semanal
`Catálogo B3 -> proventos/eventos -> DFP reapresentações/ITR -> pré-screen -> dashboard`

## Pesquisa qualitativa
O pipeline não tenta transformar anomalias em conclusões. O screener produz `PASS`, `NEAR`, `FAIL` ou `PENDING`. `NEAR/PENDING` vira fila objetiva de research; a IA ou o analista investiga somente o ponto material.

## Fontes
- B3: ativos, preços, liquidez, proventos e eventos.
- CVM: DFP/ITR.
- Tesouro Transparente: taxa real de referência.

## Economia de leitura
O frontend lê `researchDashboard/current`. Detalhes brutos podem ser consultados sob demanda, não em toda abertura da Estante.
