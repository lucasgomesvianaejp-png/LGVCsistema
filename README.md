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
