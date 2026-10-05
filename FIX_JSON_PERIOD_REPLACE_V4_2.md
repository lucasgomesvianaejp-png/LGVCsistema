# Correção v4.2 — Replace por clientId + period

## Regra

`mesmo cliente + mesmo período = replace completo daquele período`

`mesmo cliente + período novo = adicionar período`

## Preservado

- outros períodos do cliente;
- cadastro nativo;
- observações manuais;
- preferências/estratégia nativas do perfil;
- qualquer dado que não pertença ao período substituído.

## Substituído quando presente no JSON importado

- `reportSnapshots[period]` como objeto integral, sem merge de campos antigos;
- `availableReports` do período;
- `monthlyPerformance` do período;
- `dailyPerformance` cujas datas pertençam ao período;
- `positions` do fechamento/período;
- `actionPlans[period]` e demais mapas indexados por `AAAA-MM`;
- janelas de caixa/proventos ligadas ao período;
- objetos/arrays adicionais que declarem explicitamente o mesmo período.

## Relatório/PDF

Depois de salvar, o sistema mantém a versão recém-importada como fonte do workspace e seleciona imediatamente o período importado. Não recarrega a versão anterior por merge/cache antes de emitir o relatório.
