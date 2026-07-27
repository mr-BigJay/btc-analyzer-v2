"""Regime transition detection (Ch.8 §8.14)."""

from __future__ import annotations

from typing import Any

from src.intelligence.contracts import MarketCycle, MarketRegime
from src.intelligence.helpers import all_tags


def detect_transitions(
    analysis: dict[str, Any],
    *,
    market_regime: str,
    market_cycle: str,
    volatility_regime: str,
    regime_scores: dict[str, float],
) -> tuple[float, list[str]]:
    """Return (transition_probability 0–100, detected transition labels)."""
    tags = all_tags(analysis)
    detected: list[str] = []
    score = 8.0

    # Declining trend strength / divergence proxies
    if analysis.get("conflicts"):
        score += 12
        detected.append("Mixed evidence — possible regime transition")
    if "CHoCH" in tags or "Structural Reversal" in tags:
        score += 18
        detected.append("Structural break / CHoCH")
    if "Momentum" in tags and "Divergence" in str(tags):
        score += 10
        detected.append("Momentum divergence")

    # Funding / options shifts
    if "Funding" in str(tags) or "Negative Funding" in tags:
        score += 6
    if "Bullish Hedging" in tags and "Bearish Hedging" in tags:
        score += 10
        detected.append("Options sentiment shift")

    # Volatility regime changes
    if volatility_regime in ("Very Low", "Low") and "Breakout Probability" in tags:
        score += 14
        detected.append("Compression → Expansion")
    if volatility_regime in ("Elevated", "Extreme") and market_regime == MarketRegime.RANGE.value:
        score += 8
        detected.append("Volatile range — transition risk")

    # Cycle-informed transitions
    if market_cycle == MarketCycle.DISTRIBUTION.value:
        score += 10
        detected.append("Distribution → Markdown")
    if market_cycle == MarketCycle.ACCUMULATION.value and "Breakout Probability" in tags:
        score += 10
        detected.append("Range → Breakout")
    if "Uptrend" in market_regime and analysis.get("market_bias") in ("Neutral", "Slightly Bearish", "High Uncertainty"):
        score += 12
        detected.append("Uptrend → Range")

    # Competing regime scores close → transition
    ranked = sorted(regime_scores.values(), reverse=True)
    if len(ranked) >= 2 and ranked[0] > 0 and (ranked[0] - ranked[1]) < 0.8:
        score += 15
        detected.append("Competing regimes — transition likely")
        if market_regime != MarketRegime.TRANSITION.value:
            detected.append(f"Near-transition around {market_regime}")

    mtf = analysis.get("timeframe_alignment") or {}
    if mtf.get("divergent"):
        score += 10
        detected.append("Multi-timeframe divergence")

    score = max(0.0, min(95.0, score))
    # Deduplicate labels
    detected = list(dict.fromkeys(detected))
    return round(score, 1), detected[:8]
