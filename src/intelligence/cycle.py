"""Four-stage market cycle model (Ch.8 §8.4)."""

from __future__ import annotations

from typing import Any

from src.intelligence.contracts import MarketCycle, MarketRegime
from src.intelligence.helpers import all_tags, layer_map, signed


def classify_cycle(analysis: dict[str, Any], *, market_regime: str) -> tuple[str, dict[str, float]]:
    layers = layer_map(analysis)
    tags = all_tags(analysis)
    spot = layers.get("Spot") or {}
    futures = layers.get("Futures") or {}
    options = layers.get("Options") or {}
    technical = layers.get("Technical") or {}
    vol = str(analysis.get("volatility") or "Medium")

    scores = {c.value: 0.0 for c in MarketCycle}

    spot_sig = signed(str(spot.get("signal") or ""))
    fut_sig = signed(str(futures.get("signal") or ""))
    opt_sig = signed(str(options.get("signal") or ""))
    tech_sig = signed(str(technical.get("signal") or ""))

    # Accumulation
    if vol in ("Low", "Medium") and spot_sig > 0 and "Accumulation" in tags:
        scores[MarketCycle.ACCUMULATION.value] += 3.0
    if "Compression" in tags and spot_sig >= 0:
        scores[MarketCycle.ACCUMULATION.value] += 1.5
    if market_regime == MarketRegime.COMPRESSION.value:
        scores[MarketCycle.ACCUMULATION.value] += 1.2

    # Markup
    if market_regime in (MarketRegime.STRONG_UPTREND.value, MarketRegime.WEAK_UPTREND.value, MarketRegime.EXPANSION.value):
        scores[MarketCycle.MARKUP.value] += 2.5
    if "Breakout Probability" in tags or "Trend Strength" in tags:
        scores[MarketCycle.MARKUP.value] += 1.2
    if fut_sig > 0 and opt_sig >= 0 and spot_sig > 0:
        scores[MarketCycle.MARKUP.value] += 1.5
    if "Leveraged Bullish" in tags:
        scores[MarketCycle.MARKUP.value] += 0.8

    # Distribution
    if "Distribution" in tags or "Seller Dominance" in tags:
        scores[MarketCycle.DISTRIBUTION.value] += 2.5
    if "Overbought" in tags or "Overcrowded Market" in tags:
        scores[MarketCycle.DISTRIBUTION.value] += 1.5
    if fut_sig > 0 and spot_sig < 0:
        scores[MarketCycle.DISTRIBUTION.value] += 2.0  # leverage without spot
    if "Dealer Resistance" in tags or "Gamma Pinning" in tags:
        scores[MarketCycle.DISTRIBUTION.value] += 0.8

    # Markdown
    if market_regime in (MarketRegime.STRONG_DOWNTREND.value, MarketRegime.WEAK_DOWNTREND.value):
        scores[MarketCycle.MARKDOWN.value] += 2.5
    if "Long Squeeze Risk" in tags or tech_sig < 0:
        scores[MarketCycle.MARKDOWN.value] += 1.2
    if vol == "High" and spot_sig < 0:
        scores[MarketCycle.MARKDOWN.value] += 1.5
    if fut_sig < 0 and spot_sig < 0:
        scores[MarketCycle.MARKDOWN.value] += 1.0

    primary = max(scores, key=scores.get)
    if scores[primary] < 1.0:
        # Default from regime
        if "Uptrend" in market_regime or market_regime == MarketRegime.EXPANSION.value:
            primary = MarketCycle.MARKUP.value
        elif "Downtrend" in market_regime:
            primary = MarketCycle.MARKDOWN.value
        elif market_regime == MarketRegime.COMPRESSION.value:
            primary = MarketCycle.ACCUMULATION.value
        else:
            primary = MarketCycle.ACCUMULATION.value
    return primary, scores
