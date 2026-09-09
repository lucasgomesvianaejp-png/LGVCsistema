"""LGV Capital Engine — núcleo determinístico inicial.

Esta versão codifica apenas regras já fechadas na Política Geral de Ações v1.0.
Não calcula DPA/LPA/qualidade enquanto a metodologia de dados fundamentais não estiver congelada.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class StockDecision:
    ticker: str
    sector: str
    quality_score: float
    price_score: float
    pc_lgv: float
    fair_value: float
    market_price: float
    audit_grade: str = "C"
    selected_portfolio: bool = False

    @property
    def opportunity_score(self) -> float:
        return 0.65 * self.quality_score + 0.35 * self.price_score

    @property
    def price_status(self) -> str:
        if self.market_price <= self.pc_lgv:
            return "COMPRA"
        if self.market_price <= self.fair_value:
            return "RAZOAVEL"
        return "CARA"

    @property
    def eligible_for_new_capital(self) -> bool:
        return (
            self.selected_portfolio
            and self.audit_grade == "A"
            and self.price_status == "COMPRA"
        )


def pc_lgv(income_ceiling: float, fair_value: float) -> float:
    """PC_LGV = min(Teto de Renda, Valor Justo)."""
    if income_ceiling < 0 or fair_value < 0:
        raise ValueError("Teto de renda e valor justo não podem ser negativos")
    return min(income_ceiling, fair_value)


def required_yield(ipca_real_rate: float) -> float:
    """DY exigido = min(8%, max(6%, IPCA+ longo + 0,5 p.p.)).

    Taxas em formato decimal: 0.073 = 7,3%.
    """
    return min(0.08, max(0.06, ipca_real_rate + 0.005))


def rank_opportunities(stocks: Iterable[StockDecision]) -> list[StockDecision]:
    return sorted(
        stocks,
        key=lambda x: (-x.opportunity_score, -x.quality_score, x.ticker),
    )


def select_theoretical_portfolio(top15: Iterable[StockDecision]) -> list[StockDecision]:
    """Aplica limite de 2 nomes por setor sobre uma lista já ranqueada.

    A função não inventa setores nem promove empresas: preserva a ordem recebida.
    """
    sector_count: dict[str, int] = {}
    selected: list[StockDecision] = []
    for stock in top15:
        count = sector_count.get(stock.sector, 0)
        if count >= 2:
            continue
        selected.append(stock)
        sector_count[stock.sector] = count + 1
    return selected


def allocate_small_contribution(
    stocks: Iterable[StockDecision],
    contribution: float,
    current_values: Optional[dict[str, float]] = None,
) -> tuple[dict[str, float], float]:
    """Distribuição monetária inicial simples entre elegíveis por déficit.

    Esta função é deliberadamente conservadora e serve como infraestrutura.
    A regra setorial/70-30 completa deverá substituir esta rotina quando o motor
    fundamental definitivo estiver congelado.
    """
    if contribution < 0:
        raise ValueError("Aporte não pode ser negativo")
    current_values = current_values or {}
    eligible = [s for s in stocks if s.eligible_for_new_capital]
    if not eligible or contribution == 0:
        return {}, contribution

    total_current = sum(max(0.0, current_values.get(s.ticker, 0.0)) for s in eligible)
    target_total = total_current + contribution
    target_each = target_total / len(eligible)
    deficits = {
        s.ticker: max(0.0, target_each - max(0.0, current_values.get(s.ticker, 0.0)))
        for s in eligible
    }
    deficit_sum = sum(deficits.values())
    if deficit_sum <= 0:
        return {}, contribution
    allocations = {k: contribution * v / deficit_sum for k, v in deficits.items() if v > 0}
    return allocations, max(0.0, contribution - sum(allocations.values()))
