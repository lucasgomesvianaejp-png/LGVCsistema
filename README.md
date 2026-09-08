# LGV Capital — Sistema v31.12

Atualização focada na diagramação A4 e na robustez de apresentação dos relatórios mensais.

## Principais mudanças

- Nova camada de layout A4 para o PDF direto, priorizando legibilidade em vez de compressão excessiva.
- Títulos e rótulos usam pesos tipográficos padrão e espaçamento entre palavras, reduzindo o efeito de palavras "coladas" no PDF rasterizado.
- KPIs aceitam rótulos em duas linhas sem invadir os valores.
- Linhas de motores, alocação, resultados e ativos protegem o valor à direita e permitem quebra do nome à esquerda.
- Premissas e conciliação têm colunas mais flexíveis para textos longos.
- Resolução do PDF A4 aumentada para 2x e JPEG com qualidade 0,97.
- Paginação inteligente ampliada para dividir grids/listas quando um bloco não cabe em uma folha, em vez de truncar silenciosamente.
- Alias técnico `seguranca_liquidez` é consolidado automaticamente em `Segurança e liquidez`.
- Tipos de provento técnicos são traduzidos na apresentação, incluindo `DIVIDENDO_AVENUE` → `Dividendo (Avenue)`.
- `Diferença principal` da conciliação passa a ter fallback automático: posição menos patrimônio mensal, caso o JSON não traga `differenceValue` explicitamente.
- Status de conciliação e indisponibilidade da série diária passam a ter rótulos amigáveis.

## Validações realizadas

- Sintaxe dos dois blocos JavaScript internos validada com `node --check`.
- Mantida a estrutura de arquivo único do sistema atual.
- Alterações concentradas em apresentação, paginação e normalização de labels; não alteram a metodologia econômica dos relatórios.

## Teste recomendado após publicar

1. Importar o JSON corrigido do Fernando — agosto/2026.
2. Gerar o PDF A4 direto.
3. Conferir especialmente:
   - títulos dos gráficos e seções sem palavras coladas;
   - apenas 3 motores, sem `seguranca_liquidez` separado;
   - `Dividendo (Avenue)` no bloco de proventos;
   - `Diferença principal` = R$ 15,64;
   - ausência de sobreposição nas páginas de resumo, resultados, proventos e premissas.
4. Fazer uma regressão rápida com Marcus e Laísa.

## Implantação

Substituir o `index.html` atual pelo arquivo deste pacote e publicar normalmente no Vercel/GitHub.
