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

---

# Atualização — Módulo Institucional de Investimentos

Esta versão inicia a transformação do LGV Capital Sistema em uma plataforma única de clientes + research.

## Incluído

- Nova navegação lateral com grupo **Investimentos**.
- Novo módulo funcional **Investimentos > Ações**.
- Abas: Estante, Screener, Top 15, Carteira teórica e Research.
- Perfil completo de ativo em página, não modal.
- Snapshot inicial da Política LGV v1.0 para validar a UX sem liberar recomendação financeira.
- Estrutura modular nova em `src/investments/` e `styles/` sem reescrever o módulo legado de clientes.
- Schema inicial de research em `supabase/schema.sql`.
- LGV Engine inicial em Python com regras determinísticas já fechadas e testes automatizados.
- Arquitetura documentada em `docs/RESEARCH_ARCHITECTURE.md`.

## Segurança da integração de research

O frontend não contém chave `service_role` de Supabase. Nesta fase o banco de research foi desenhado para ser acessado por um backend confiável; Firebase continua responsável pelo login e dados atuais de clientes.

## Estado do módulo Ações

A interface é funcional, porém os campos de valuation aparecem como pendentes. Nenhuma recomendação real é liberada pelo snapshot local. A próxima camada será conectar o LGV Engine e os ingestores auditados ao banco.

## Validação desta versão

- JavaScript do módulo novo: `node --check` aprovado.
- Dois blocos JavaScript existentes do `index.html`: sintaxe aprovada após integração.
- IDs HTML duplicados: nenhum encontrado.
- Testes do LGV Engine: 7/7 aprovados.
