"""Mandatory risk explanations (Ch.15 §15.17)."""

from __future__ import annotations

from typing import Any

from src.risk.contracts import CategoryScore, RiskLevel


def build_risk_explanation(
    *,
    crs: float,
    risk_level: str,
    categories: dict[str, CategoryScore],
    no_trade: bool,
    no_trade_reasons: list[str],
    market_bias: str | None = None,
) -> str:
    drivers: list[str] = []
    # Top category contributors
    ranked = sorted(categories.values(), key=lambda c: c.score, reverse=True)
    for cat in ranked[:3]:
        if cat.score >= 45 and cat.drivers:
            drivers.append(cat.drivers[0])
        elif cat.score >= 45:
            drivers.append(f"{cat.name} risk elevated ({cat.score:.0f})")

    bias_note = ""
    if market_bias and "Bull" in market_bias:
        bias_note = " Although directional bias remains bullish,"
    elif market_bias and "Bear" in market_bias:
        bias_note = " Although directional bias remains bearish,"

    if no_trade:
        why = "; ".join(no_trade_reasons[:3]) or "capital preservation controls"
        return (
            f"No Trade Zone active. Execution recommendations are suppressed because {why}. "
            f"Composite Risk Score={crs:.0f} ({risk_level})."
        )

    if risk_level in (RiskLevel.HIGH.value, RiskLevel.EXTREME.value, RiskLevel.MODERATE.value) and crs > 40:
        detail = " and ".join(drivers[:2]) if drivers else "elevated cross-factor risk"
        return (
            f"Execution risk is elevated due to {detail}.{bias_note} "
            f"reduced exposure is recommended until market stress and related risks decline. "
            f"CRS={crs:.0f} ({risk_level})."
        )

    if drivers:
        return f"Execution risk is {risk_level.lower()} (CRS={crs:.0f}). Primary factors: " + "; ".join(drivers[:3]) + "."
    return f"Execution risk is {risk_level.lower()} (CRS={crs:.0f}) with no dominant elevated drivers."


def risk_reward_assessment(*, crs: float, confidence: float, no_trade: bool) -> str:
    from src.risk.contracts import RiskReward

    if no_trade or crs >= 70 or confidence < 50:
        return RiskReward.UNFAVORABLE.value
    if crs <= 35 and confidence >= 70:
        return RiskReward.FAVORABLE.value
    return RiskReward.BALANCED.value
