# LGV Engine

Núcleo determinístico inicial do módulo de Ações.

Nesta entrega, somente regras já fechadas foram codificadas:

- `PC_LGV = min(Teto de Renda, Valor Justo)`;
- DY exigido com piso de 6%, prêmio de 0,5 p.p. e teto de 8%;
- Nota de Oportunidade 65% Qualidade + 35% Preço;
- Compra nova somente para carteira selecionada + Grau A + faixa Compra;
- limite de dois ativos por setor na seleção;
- testes de invariantes.

A normalização fundamental (DPA, LPA, payout, scores de Qualidade) fica fora até a política operacional ser congelada. Isso evita codificar uma regra ainda em discussão.
