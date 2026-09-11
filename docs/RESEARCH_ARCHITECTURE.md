# LGV Capital — Arquitetura Research Firebase

## Objetivo
Usar o mesmo projeto Firebase `lvg-invest` do sistema de clientes, mantendo um único login e evitando um segundo banco.

## Camadas
1. **Firebase Auth**: login já existente.
2. **Firestore**: Clientes + Research, em coleções separadas.
3. **GitHub Actions + Firebase Admin**: ingestão segura de fontes oficiais.
4. **LGV Engine**: screening/cálculos determinísticos.
5. **Frontend**: lê somente o documento agregado `researchDashboard/current` para a tela principal.

## Coleções
- `clients`, `clientData`: legado atual, não alterado.
- `researchIssuers`
- `researchAssets`
- `researchMarket`
- `researchDividends`
- `researchCorporateActions`
- `researchFundamentals`
- `researchTreasury`
- `researchScreening`
- `researchScreeningSnapshots`
- `researchValuations`
- `researchIngestionRuns`
- `researchMeta`
- `researchDashboard`

## Estratégia de custo
O Firestore não recebe uma linha por pregão. `researchMarket/{ticker}` guarda estatísticas anuais e ADTV 12M. Proventos e eventos são agrupados por ticker. CVM é agrupada por emissor/período. A interface principal consome um único documento agregado.

## Segurança
A Service Account existe somente no GitHub Secret. O navegador usa a configuração web pública do Firebase que já existia no sistema e não recebe credenciais administrativas.
