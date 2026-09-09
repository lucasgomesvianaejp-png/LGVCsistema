# LGV Capital — arquitetura do módulo de Research

## Estado desta entrega

O sistema atual de clientes/relatórios permanece no Firebase sem migração.
Foi criado o primeiro módulo institucional `Investimentos > Ações`, isolado em `src/investments/stocks.js` e `styles/investments.css`.

O módulo abre usando um snapshot local da Política LGV v1.0 apenas para validar navegação e UX. Campos de valuation e recomendação ficam `Pendente` até o motor auditado ser conectado.

## Arquitetura alvo

1. Firebase Auth + Firestore: clientes e relatórios existentes.
2. Supabase/Postgres: dados institucionais de research.
3. Backend server-side: ponte entre o usuário autenticado e o banco de research; secrets/service_role nunca vão para o navegador.
4. LGV Engine: Python/SQL determinístico para screening, métricas, valuation, ranking e portfólio.
5. IA: somente fila de exceções qualitativas (`lgv_research_flags`).

## Próximas implementações

- Criar projeto Supabase e aplicar `supabase/schema.sql`.
- Implementar autenticação do backend com token Firebase e autorização administrativa.
- Criar ingestores CVM/B3/Tesouro.
- Implementar `LGV Engine` e testes automatizados.
- Trocar o provider local de `stocks.js` por endpoint autenticado do backend.
- Integrar a Estante com posições e políticas de alocação dos clientes.
