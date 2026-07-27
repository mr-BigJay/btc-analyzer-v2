"""Scenario generation (Ch.6 §6.10) — probabilistic, not deterministic."""

from __future__ import annotations

from src.analysis.contracts import LayerResult, Scenario, SignalBias
from src.analysis.context import MarketContext


def generate_scenarios(
    *,
    market_bias: str,
    confidence: float,
    ctx: MarketContext,
    layer_results: list[LayerResult],
) -> list[Scenario]:
    price = ctx.mark_price or (ctx.closes[-1] if ctx.closes else None)
    atr_proxy = None
    for r in layer_results:
        if r.layer == "Technical" and r.details.get("atr"):
            atr_proxy = float(r.details["atr"])
            break
    if atr_proxy is None and price:
        atr_proxy = price * 0.01

    bull_p = bear_p = side_p = 0.0
    if market_bias in (SignalBias.BULLISH.value, SignalBias.SLIGHTLY_BULLISH.value):
        bull_p = 0.45 + confidence / 400
        side_p = 0.30
        bear_p = 1.0 - bull_p - side_p
    elif market_bias in (SignalBias.BEARISH.value, SignalBias.SLIGHTLY_BEARISH.value):
        bear_p = 0.45 + confidence / 400
        side_p = 0.30
        bull_p = 1.0 - bear_p - side_p
    elif market_bias == SignalBias.HIGH_UNCERTAINTY.value:
        bull_p, side_p, bear_p = 0.30, 0.40, 0.30
    else:
        bull_p, side_p, bear_p = 0.28, 0.44, 0.28

    # Normalize
    total = bull_p + side_p + bear_p
    bull_p, side_p, bear_p = bull_p / total, side_p / total, bear_p / total

    scenarios = [
        Scenario(
            name="Bullish Continuation",
            probability=round(bull_p * 100, 1),
            trigger="Hold above session VWAP / HL structure with supportive funding",
            target_zones=_targets(price, atr_proxy, direction=1),
            invalidation=(price - 1.5 * atr_proxy) if price and atr_proxy else None,
            confidence=min(100.0, confidence + 5) if "Bullish" in market_bias else confidence * 0.7,
        ),
        Scenario(
            name="Sideways Consolidation",
            probability=round(side_p * 100, 1),
            trigger="Range between nearest liquidity pools / max pain magnet",
            target_zones=_targets(price, atr_proxy, direction=0),
            invalidation=None,
            confidence=max(40.0, 80 - abs(50 - confidence) * 0.3),
        ),
        Scenario(
            name="Bearish Reversal",
            probability=round(bear_p * 100, 1),
            trigger="Break of HL / BOS down with rising PCR or crowded longs",
            target_zones=_targets(price, atr_proxy, direction=-1),
            invalidation=(price + 1.5 * atr_proxy) if price and atr_proxy else None,
            confidence=min(100.0, confidence + 5) if "Bearish" in market_bias else confidence * 0.7,
        ),
    ]
    scenarios.sort(key=lambda s: s.probability, reverse=True)
    return scenarios


def _targets(price: float | None, atr: float | None, direction: int) -> list[float]:
    if price is None or atr is None:
        return []
    if direction > 0:
        return [round(price + atr, 2), round(price + 2 * atr, 2)]
    if direction < 0:
        return [round(price - atr, 2), round(price - 2 * atr, 2)]
    return [round(price - 0.5 * atr, 2), round(price + 0.5 * atr, 2)]
