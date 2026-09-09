# LGV Research — implantação

## Estado desta entrega

O módulo de clientes/relatórios continua em Firebase/Firestore.
O módulo institucional de research foi preparado para um projeto Supabase/PostgreSQL **dedicado**.

O projeto Supabase conectado durante o desenvolvimento contém tabelas de folha de pagamento. Ele não foi alterado.

## 1. Banco dedicado

Crie um projeto Supabase exclusivo para LGV Research e execute, nessa ordem:

1. `supabase/schema.sql`
2. `supabase/seed_current_shelf.sql`

O seed serve apenas para preservar o snapshot estrutural legado enquanto a nova base é construída. Ele não libera recomendação.

## 2. Segredos no Vercel

Configure somente no servidor:

- `FIREBASE_WEB_API_KEY`
- `LGV_ALLOWED_EMAILS`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

A `service_role` nunca deve ser colocada em JavaScript entregue ao navegador.

## 3. Segredos no GitHub Actions

- `LGV_SUPABASE_URL`
- `LGV_SUPABASE_SERVICE_ROLE_KEY`

## 4. Bootstrap inicial

Execute manualmente o workflow semanal uma vez. Ele carrega:

- catálogo B3 / vínculo com CVM;
- proventos e eventos societários B3;
- ITR do ano corrente;
- DFP dos cinco exercícios completos;
- pré-screening.

Depois execute o workflow diário para atualizar COTAHIST corrente, Tesouro e o screener.

## 5. Funcionamento normal

### Diário

`B3 preço/volume -> Tesouro -> screener`

### Semanal

`B3 emissores/proventos/eventos -> CVM -> screener`

### Research humano/IA

Somente a fila `lgv_research_queue_latest`, formada por casos `NEAR/PENDING`, deve gerar pesquisa qualitativa adicional.

## 6. Critério de segurança

O pré-screen pode reduzir o universo, mas não gera recomendação. Valuation e ordem só devem ser liberados quando a metodologia fundamental definitiva preencher `lgv_valuations` e o ativo atingir o grau de auditoria exigido.
