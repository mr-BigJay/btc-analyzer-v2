"""Market narrative detection (Ch.7 §7.6) — one primary narrative at a time."""

from __future__ import annotations

from typing import Any

from src.ai.contracts import EvidenceItem
from src.analysis.contracts import MarketAnalysisOutput, SignalBias


NARRATIVES = (
    "Bullish Trend Expansion",
    "Short Squeeze",
    "Long Squeeze Risk",
    "Distribution",
    "Accumulation",
    "Range / Indecision",
    "Volatility Expansion Setup",
    "Liquidity Sweep Setup",
)


def detect_narrative(
    analysis: MarketAnalysisOutput | dict[str, Any],
    evidence: list[EvidenceItem],
) -> tuple[str, list[str]]:
    """Return (primary_narrative, supporting_bullets). Only one primary narrative."""
    if isinstance(analysis, MarketAnalysisOutput):
        bias = analysis.market_bias
        regime = analysis.market_regime
        volatility = analysis.volatility
        tags = {t for r in analysis.layer_results for t in (r.get("tags") or [])}
        layer_map = {r.get("layer"): r for r in analysis.layer_results}
    else:
        bias = str(analysis.get("market_bias") or SignalBias.NEUTRAL.value)
        regime = str(analysis.get("market_regime") or "Range")
        volatility = str(analysis.get("volatility") or "Medium")
        tags = set()
        layer_map = {}
        for r in analysis.get("layer_results") or []:
            tags.update(r.get("tags") or [])
            layer_map[r.get("layer")] = r

    futures = layer_map.get("Futures") or {}
    spot = layer_map.get("Spot") or {}
    options = layer_map.get("Options") or {}
    fut_tags = set(futures.get("tags") or [])
    spot_tags = set(spot.get("tags") or [])
    opt_tags = set(options.get("tags") or [])

    scores: dict[str, float] = {n: 0.0 for n in NARRATIVES}

    # Bullish Trend Expansion
    if bias in (SignalBias.BULLISH.value, SignalBias.SLIGHTLY_BULLISH.value):
        scores["Bullish Trend Expansion"] += 2.0
    if "Accumulation" in spot_tags or "Buyer Dominance" in spot_tags:
        scores["Bullish Trend Expansion"] += 1.2
        scores["Accumulation"] += 1.5
    if "Leveraged Bullish" in fut_tags or "positive" in str(futures.get("summary", "")).lower():
        scores["Bullish Trend Expansion"] += 0.8
    if "Dealer Support" in opt_tags or "Bullish Hedging" in opt_tags:
        scores["Bullish Trend Expansion"] += 1.0
    if regime in ("Trend", "Breakout"):
        scores["Bullish Trend Expansion"] += 1.0

    # Short Squeeze
    if "Short Squeeze Risk" in fut_tags or "Short Squeeze Risk" in tags:
        scores["Short Squeeze"] += 3.0
    if bias in (SignalBias.BULLISH.value, SignalBias.SLIGHTLY_BULLISH.value) and "Negative Funding" in fut_tags:
        scores["Short Squeeze"] += 1.5

    # Long Squeeze / Distribution
    if "Long Squeeze Risk" in fut_tags or "Long Squeeze Risk" in tags:
        scores["Long Squeeze Risk"] += 3.0
    if "Distribution" in spot_tags or "Seller Dominance" in spot_tags:
        scores["Distribution"] += 2.0
    if bias in (SignalBias.BEARISH.value, SignalBias.SLIGHTLY_BEARISH.value):
        scores["Distribution"] += 1.5
        scores["Long Squeeze Risk"] += 0.5

    # Range / Volatility / Liquidity
    if bias in (SignalBias.NEUTRAL.value, SignalBias.HIGH_UNCERTAINTY.value) or regime == "Range":
        scores["Range / Indecision"] += 2.0
    if volatility == "High" or "Expansion" in tags or regime == "Breakout":
        scores["Volatility Expansion Setup"] += 1.8
    if "Compression" in tags:
        scores["Volatility Expansion Setup"] += 1.2
    if "Sweep Probability" in tags or "Liquidity Above" in tags or "Liquidity Below" in tags:
        scores["Liquidity Sweep Setup"] += 1.5

    if bias == SignalBias.HIGH_UNCERTAINTY.value:
        scores["Range / Indecision"] += 1.5

    primary = max(scores, key=scores.get)
    if scores[primary] < 1.0:
        primary = "Range / Indecision"

    bullets = _narrative_bullets(primary, evidence, tags)
    return primary, bullets


def _narrative_bullets(narrative: str, evidence: list[EvidenceItem], tags: set[str]) -> list[str]:
    top = [e.evidence for e in evidence[:4] if e.evidence]
    catalog = {
        "Bullish Trend Expansion": [
            "Spot accumulation / buyer dominance present",
            "Futures open interest supportive of upside leverage",
            "Options dealers / hedging constructive",
            "Structure or breakout confirmation",
        ],
        "Short Squeeze": [
            "Negative funding with rising price pressure",
            "Crowded short exposure vulnerable to liquidations",
        ],
        "Long Squeeze Risk": [
            "Crowded longs / funding imbalance",
            "Liquidation cascade risk on downside breaks",
        ],
        "Distribution": [
            "Weak spot demand / seller dominance",
            "High leverage with failed upside follow-through",
        ],
        "Accumulation": [
            "Quiet absorption / buyer dominance without chase",
        ],
        "Range / Indecision": [
            "Mixed or low-conviction cross-layer signals",
            "No dominant directional narrative",
        ],
        "Volatility Expansion Setup": [
            "Compression/expansion volatility regime shift",
        ],
        "Liquidity Sweep Setup": [
            "Liquidity pools / stop clusters nearby",
        ],
    }
    base = catalog.get(narrative, [])
    merged = list(dict.fromkeys(top + base))
    if tags:
        merged.append(f"Active tags: {', '.join(sorted(list(tags))[:6])}")
    return merged[:6]
