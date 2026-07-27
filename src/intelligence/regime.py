"""Market regime classification (Ch.8 §8.3) — one primary regime."""

from __future__ import annotations

from typing import Any

from src.intelligence.contracts import MarketRegime
from src.intelligence.helpers import all_tags, layer_map, signed


def classify_regime(analysis: dict[str, Any]) -> tuple[str, dict[str, float]]:
    layers = layer_map(analysis)
    tags = all_tags(analysis)
    bias = str(analysis.get("market_bias") or "Neutral")
    vol = str(analysis.get("volatility") or "Medium")
    structure = layers.get("Market Structure") or {}
    technical = layers.get("Technical") or {}
    spot = layers.get("Spot") or {}

    scores = {r.value: 0.0 for r in MarketRegime}

    struct_sig = signed(str(structure.get("signal") or ""))
    tech_sig = signed(str(technical.get("signal") or ""))
    spot_sig = signed(str(spot.get("signal") or ""))
    struct_conf = float(structure.get("confidence") or 50) / 100.0
    tech_conf = float(technical.get("confidence") or 50) / 100.0

    if "Compression" in tags or vol == "Low":
        scores[MarketRegime.COMPRESSION.value] += 2.5
    if "Expansion" in tags or vol == "High" or "High Volatility" in tags:
        scores[MarketRegime.EXPANSION.value] += 2.5

    if struct_sig > 0 and tech_sig > 0 and spot_sig >= 0:
        strength = (struct_conf + tech_conf) / 2
        if strength >= 0.65 and "Trend Strength" in tags:
            scores[MarketRegime.STRONG_UPTREND.value] += 3.0 + strength
        else:
            scores[MarketRegime.WEAK_UPTREND.value] += 2.2 + strength * 0.5
    elif struct_sig > 0 or ("Bullish" in bias and tech_sig >= 0):
        scores[MarketRegime.WEAK_UPTREND.value] += 1.8

    if struct_sig < 0 and tech_sig < 0 and spot_sig <= 0:
        strength = (struct_conf + tech_conf) / 2
        if strength >= 0.65 and "Trend Strength" in tags:
            scores[MarketRegime.STRONG_DOWNTREND.value] += 3.0 + strength
        else:
            scores[MarketRegime.WEAK_DOWNTREND.value] += 2.2 + strength * 0.5
    elif struct_sig < 0 or ("Bearish" in bias and tech_sig <= 0):
        scores[MarketRegime.WEAK_DOWNTREND.value] += 1.8

    if bias in ("Neutral", "High Uncertainty") or abs(struct_sig) < 0.25:
        scores[MarketRegime.RANGE.value] += 2.0
    if analysis.get("conflicts"):
        scores[MarketRegime.TRANSITION.value] += 1.5
        scores[MarketRegime.RANGE.value] += 0.5
    if "CHoCH" in tags or "Structural Reversal" in tags:
        scores[MarketRegime.TRANSITION.value] += 2.5

    # Only one primary regime
    primary = max(scores, key=scores.get)
    if scores[primary] < 1.0:
        primary = MarketRegime.RANGE.value
    return primary, scores
