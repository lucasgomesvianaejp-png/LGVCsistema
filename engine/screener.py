"""LGV Screener — camada barata e conservadora antes do research profundo."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PreScreenInput:
    ticker: str
    sector: str | None
    adtv_12m: float | None
    raw_dy_5y: float | None
    latest_profit: float | None
    has_corporate_action_5y: bool = False
    dividend_years: int = 0


@dataclass(frozen=True)
class PreScreenResult:
    status: str
    passes_liquidity: Optional[bool]
    passes_dividend: Optional[bool]
    passes_profit: Optional[bool]
    fail_reasons: tuple[str, ...] = field(default_factory=tuple)
    near_reasons: tuple[str, ...] = field(default_factory=tuple)


def pre_screen(
    item: PreScreenInput,
    liquidity_min: float = 1_000_000,
    liquidity_near: float = 1_200_000,
    dy_min: float = 0.06,
    dy_near: float = 0.055,
    complete_years: int = 5,
    excluded_sector_terms: tuple[str, ...] = ('varejo', 'aviacao', 'aviação'),
) -> PreScreenResult:
    fail: list[str] = []
    near: list[str] = []

    sector = (item.sector or '').lower()
    if sector and any(term in sector for term in excluded_sector_terms):
        fail.append('SETOR_EXCLUIDO')

    liquidity_pass: Optional[bool] = None
    if item.adtv_12m is not None:
        liquidity_pass = item.adtv_12m >= liquidity_min
        if item.adtv_12m < liquidity_min:
            fail.append('LIQUIDEZ_ABAIXO_MINIMO')
        elif item.adtv_12m < liquidity_near:
            near.append('LIQUIDEZ_PROXIMA_AO_CORTE')
    else:
        near.append('LIQUIDEZ_PENDENTE')

    dividend_pass: Optional[bool] = None
    if item.has_corporate_action_5y:
        near.append('AJUSTE_EVENTO_SOCIETARIO_NECESSARIO')
    elif item.dividend_years < complete_years or item.raw_dy_5y is None:
        near.append('HISTORICO_DY_INCOMPLETO')
    else:
        dividend_pass = item.raw_dy_5y >= dy_min
        if item.raw_dy_5y < dy_near:
            fail.append('DY_5A_CLARAMENTE_ABAIXO_MINIMO')
        elif item.raw_dy_5y < dy_min:
            near.append('DY_5A_ZONA_DE_APROXIMACAO')

    profit_pass: Optional[bool] = None
    if item.latest_profit is None:
        near.append('LUCRO_ANUAL_PENDENTE')
    else:
        profit_pass = item.latest_profit > 0
        # Resultado reportado negativo merece auditoria; não é eliminação cega por possível não recorrência.
        if not profit_pass:
            near.append('LUCRO_REPORTADO_NAO_POSITIVO_REQUER_AUDITORIA')

    if fail:
        status = 'FAIL'
    elif near:
        status = 'NEAR'
    elif liquidity_pass and dividend_pass and profit_pass:
        status = 'PASS'
    else:
        status = 'PENDING'

    return PreScreenResult(
        status=status,
        passes_liquidity=liquidity_pass,
        passes_dividend=dividend_pass,
        passes_profit=profit_pass,
        fail_reasons=tuple(dict.fromkeys(fail)),
        near_reasons=tuple(dict.fromkeys(near)),
    )
