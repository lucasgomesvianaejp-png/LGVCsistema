# LGV Capital Sistema — correção v4.1

## Problema corrigido
A v4 passou a consultar a subcoleção `clients/{clientId}/observations` ao abrir qualquer perfil.
Se as regras atuais do Firestore ainda não autorizarem essa subcoleção, o Firestore retorna `permission-denied` / `Missing or insufficient permissions`.
Como a consulta estava dentro do mesmo `Promise.all` usado para carregar cadastro e histórico, a falha das observações bloqueava o perfil inteiro.

## Comportamento da v4.1
- Cadastro e histórico do cliente continuam carregando mesmo que a subcoleção de observações ainda esteja bloqueada.
- A aba Observações informa que a regra precisa ser publicada.
- Depois de publicar a regra abaixo, a aba Observações passa a funcionar normalmente.

## Regra a MESCLAR às regras atuais do Firestore
Dentro de `match /databases/{database}/documents { ... }`:

```text
match /clients/{clientId}/observations/{observationId} {
  allow read, create, update, delete: if request.auth != null;
}
```

Não substitua as regras atuais por esse trecho; apenas acrescente-o no bloco principal.
