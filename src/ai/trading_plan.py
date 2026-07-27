"""Intraday Trading Plan generator (Ch.7 §7.14) — advisory only."""

from __future__ import annotations

from typing import Any

from src.ai.contracts import ScenarioAssessment, TradingPlanSpec
from src.analysis.contracts import SignalBias


def build_trading_plan(
    *,
    market_bias: str,
    confidence: float,
    risk_level: str,
    scenarios: list[ScenarioAssessment],
    layer_results: list[dict[str, Any]],
) -> TradingPlanSpec:
    primary = scenarios[0] if scenarios else None
    mark = _mark_price(layer_results)
    atr = _atr(layer_results) or ((mark * 0.01) if mark else None)

    # Constraints: never recommend excessive leverage; escalate to no_trade on weak evidence
    if (
        confidence < 55
        or market_bias in (SignalBias.NEUTRAL.value, SignalBias.HIGH_UNCERTAINTY.value)
        or "Extreme" in risk_level
        or "High Risk" == risk_level
    ):
        return TradingPlanSpec(
            preferred_direction="no_trade",
            confirmation_conditions=[
                "Wait for cross-layer confirmation (Spot + Futures or Options aligned)",
                "Require structure break/hold with volume before engagement",
            ],
            session_notes=(
                "Evidence quality or risk posture does not support an actionable intraday plan. "
                "Stand aside; preserve capital."
            ),
            confidence=confidence,
            position_sizing_guidance="Flat — no position while uncertainty/risk is elevated.",
        )

    bullish = market_bias in (SignalBias.BULLISH.value, SignalBias.SLIGHTLY_BULLISH.value)
    direction = "long" if bullish else "short"

    entry: list[float] = []
    targets: list[float] = []
    stop = None
    rr = None
    invalidation = primary.invalidation if primary else None

    if mark and atr:
        if bullish:
            entry = [round(mark - 0.35 * atr, 2), round(mark + 0.15 * atr, 2)]
            targets = list(primary.target_zones) if primary and primary.target_zones else [
                round(mark + atr, 2),
                round(mark + 2 * atr, 2),
            ]
            stop = round(mark - 1.2 * atr, 2)
            invalidation = invalidation or stop
        else:
            entry = [round(mark - 0.15 * atr, 2), round(mark + 0.35 * atr, 2)]
            targets = list(primary.target_zones) if primary and primary.target_zones else [
                round(mark - atr, 2),
                round(mark - 2 * atr, 2),
            ]
            stop = round(mark + 1.2 * atr, 2)
            invalidation = invalidation or stop

        if entry and stop and targets:
            risk = abs(((entry[0] + entry[1]) / 2) - stop)
            reward = abs(targets[0] - ((entry[0] + entry[1]) / 2))
            rr = round(reward / risk, 2) if risk else None

    confirmations = [
        f"Primary scenario '{primary.name if primary else 'n/a'}' remains highest probability",
        "No sudden opposing liquidation cascade against preferred direction",
    ]
    if bullish:
        confirmations.append("Hold above nearby structure support / buyer defense")
    else:
        confirmations.append("Rejection at resistance / seller absorption confirmed")

    sizing = "Risk ≤0.5–1% of equity; avoid stacking leverage. Reduce size if funding is extreme."
    if "Elevated" in risk_level:
        sizing = "Risk ≤0.5% of equity; half-size only until risk cools."

    notes = (
        f"Advisory plan aligned with {market_bias} bias. "
        f"Adapt as new Analysis Engine evidence arrives. "
        f"Leading scenario probability {primary.probability if primary else 0:.0f}%."
    )

    return TradingPlanSpec(
        preferred_direction=direction,
        entry_zone=entry,
        confirmation_conditions=confirmations,
        target_levels=targets,
        stop_loss_zone=stop,
        risk_reward=rr,
        position_sizing_guidance=sizing,
        session_notes=notes,
        invalidation=invalidation,
        confidence=confidence,
        advisory=True,
    )


def _mark_price(layer_results: list[dict[str, Any]]) -> float | None:
    for row in layer_results:
        details = row.get("details") or {}
        for key in ("mark_price", "price", "spot_price", "close"):
            if details.get(key) is not None:
                try:
                    return float(details[key])
                except (TypeError, ValueError):
                    pass
    return None


def _atr(layer_results: list[dict[str, Any]]) -> float | None:
    for row in layer_results:
        if row.get("layer") == "Technical":
            details = row.get("details") or {}
            if details.get("atr") is not None:
                try:
                    return float(details["atr"])
                except (TypeError, ValueError):
                    return None
    return None
