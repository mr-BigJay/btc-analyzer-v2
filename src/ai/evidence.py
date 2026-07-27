"""Evidence aggregation + signal prioritization (Ch.7 §7.4–§7.5)."""

from __future__ import annotations

from typing import Any

from src.ai.contracts import EvidenceItem
from src.analysis.contracts import MarketAnalysisOutput, SignalBias


# Historical reliability priors (placeholders for learning loop Ch.7 §7.17)
LAYER_RELIABILITY: dict[str, float] = {
    "Spot": 0.85,
    "Futures": 0.80,
    "Options": 0.82,
    "Technical": 0.70,
    "Market Structure": 0.78,
    "Liquidity": 0.72,
    "Pattern Detection": 0.55,
    "Volatility": 0.65,
}


def _layer_rows(analysis: MarketAnalysisOutput | dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(analysis, MarketAnalysisOutput):
        return list(analysis.layer_results or [])
    return list(analysis.get("layer_results") or [])


def aggregate_evidence(analysis: MarketAnalysisOutput | dict[str, Any]) -> list[EvidenceItem]:
    """Each layer contributes evidence — not a final decision (Ch.7 §7.4)."""
    items: list[EvidenceItem] = []
    for row in _layer_rows(analysis):
        layer = str(row.get("layer", "Unknown"))
        signal = str(row.get("signal", SignalBias.NEUTRAL.value))
        conf = float(row.get("confidence") or 50)
        summary = str(row.get("summary") or f"{layer} signal: {signal}")
        tags = list(row.get("tags") or [])
        dq = float(row.get("data_quality") if row.get("data_quality") is not None else 1.0)
        items.append(
            EvidenceItem(
                layer=layer,
                evidence=summary,
                signal=signal,
                confidence=conf,
                tags=tags,
                data_quality=max(0.0, min(1.0, dq)),
            )
        )
    return prioritize_signals(items, analysis)


def prioritize_signals(
    items: list[EvidenceItem],
    analysis: MarketAnalysisOutput | dict[str, Any],
) -> list[EvidenceItem]:
    """Rank signals by reliability, regime, confirmation, freshness, quality (Ch.7 §7.5)."""
    if isinstance(analysis, MarketAnalysisOutput):
        regime = analysis.market_regime
        weights = analysis.weights or {}
        conflicts = analysis.conflicts or []
        mtf = analysis.timeframe_alignment or {}
    else:
        regime = str(analysis.get("market_regime") or "Range")
        weights = dict(analysis.get("weights") or {})
        conflicts = list(analysis.get("conflicts") or [])
        mtf = dict(analysis.get("timeframe_alignment") or {})

    aligned = bool(mtf.get("aligned"))
    bullish = [i for i in items if "Bullish" in i.signal]
    bearish = [i for i in items if "Bearish" in i.signal]

    for item in items:
        reliability = LAYER_RELIABILITY.get(item.layer, 0.5)
        weight = float(weights.get(item.layer, 0.05))
        conf_factor = item.confidence / 100.0
        quality = item.data_quality

        # Cross-layer confirmation boost
        confirmation = 0.0
        if "Bullish" in item.signal and len(bullish) >= 3:
            confirmation = 0.15
        elif "Bearish" in item.signal and len(bearish) >= 3:
            confirmation = 0.15
        elif item.signal == SignalBias.NEUTRAL.value:
            confirmation = 0.0

        # Pattern without volume / weak confirmation → low priority
        if item.layer == "Pattern Detection" and conf_factor < 0.55:
            confirmation -= 0.15

        # Regime affinity
        regime_boost = 0.0
        if regime in ("Trend", "Breakout") and item.layer in ("Market Structure", "Technical", "Liquidity"):
            regime_boost = 0.08
        if regime == "Compression" and item.layer == "Volatility":
            regime_boost = 0.10

        freshness = 0.05 if aligned else 0.0
        conflict_penalty = 0.08 if conflicts and item.layer in str(conflicts) else 0.0

        priority = (
            0.35 * reliability
            + 0.25 * weight
            + 0.20 * conf_factor
            + 0.10 * quality
            + confirmation
            + regime_boost
            + freshness
            - conflict_penalty
        )
        item.priority = max(0.05, min(1.0, priority))

    items.sort(key=lambda e: e.priority, reverse=True)
    return items


def dominant_layers(evidence: list[EvidenceItem], *, n: int = 5) -> list[EvidenceItem]:
    return evidence[:n]
