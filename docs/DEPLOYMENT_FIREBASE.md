# LGV Research no mesmo Firebase (`lvg-invest`)

## 1. Service Account — único segredo necessário
No Google Cloud Console/Firebase do projeto `lvg-invest`, crie/baixe uma Service Account com acesso ao Firestore.
No GitHub do repositório: **Settings → Secrets and variables → Actions → New repository secret**.
Nome: `FIREBASE_SERVICE_ACCOUNT_LGV_INVEST`.
Valor: conteúdo integral do JSON.

**Nunca** cole esse JSON em `index.html`, `.env` versionado ou JavaScript do navegador.

## 2. Regras do Firestore
O arquivo `firebase/firestore-research.rules.snippet` é deliberadamente um trecho. Mescle-o às regras atuais para não quebrar `clients` e `clientData`.
O navegador só precisa ler `researchDashboard/current`; o restante pode ser fechado depois se quiser.

## 3. Primeira carga
GitHub → Actions → `LGV Research Bootstrap` → Run workflow.
Ele baixa B3/CVM/Tesouro, grava dados agregados no mesmo Firestore, roda o pré-screen e publica `researchDashboard/current`.

## 4. Rotina
- `LGV Research Daily`: B3 + Tesouro + screener + dashboard.
- `LGV Research Weekly`: catálogo/proventos/CVM + screener + dashboard.

## 5. Hospedagem sem custo comercial
Para não depender do Vercel Hobby (restrito a uso não comercial), use Firebase Hosting no mesmo projeto:

```bash
npm install -g firebase-tools
firebase login
firebase use lvg-invest
firebase deploy --only hosting
```

## Modelo de custo
A persistência foi desenhada para NÃO guardar uma linha Firestore por pregão nem uma linha por conta CVM.
- mercado: 1 documento por ticker com estatísticas anuais + ADTV 12M;
- dividendos/eventos: 1 documento por ticker;
- fundamentos: 1 documento por emissor com períodos selecionados;
- screener: 1 snapshot agregado por data;
- dashboard: 1 documento atual.
Isso reduz leituras, gravações e armazenamento.
