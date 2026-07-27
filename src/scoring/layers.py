"""Per-layer score normalization to [-100, +100] (Ch.9 §9.4–§9.5)."""

from __future__ import annotations

from typing import Any

from src.analysis.contracts import LayerResult, MarketAnalysisOutput, SignalBias
from src.scoring.contracts import LAYER_NAMES, interpret_layer_score


def layer_score_from_result(row: LayerResult | dict[str, Any]) -> float:
    """Map a layer result to a signed score in [-100, +100]."""
    if isinstance(row, LayerResult):
        signal = row.signal
        confidence = float(row.confidence)
        quality = float(row.data_quality)
        signed = row.signed_score  # [-1, 1]
    else:
        signal = str(row.get("signal") or SignalBias.NEUTRAL.value)
        confidence = float(row.get("confidence") or 50)
        quality = float(row.get("data_quality") if row.get("data_quality") is not None else 1.0)
        signed = _signed(signal, confidence)

    # Base from signed score × 100, tempered by data quality
    raw = signed * 100.0
    # When quality is low, pull toward neutral (explicit uncertainty)
    score = raw * (0.35 + 0.65 * max(0.0, min(1.0, quality)))
    return round(max(-100.0, min(100.0, score)), 2)


def score_all_layers(analysis: MarketAnalysisOutput | dict[str, Any]) -> dict[str, float]:
    if isinstance(analysis, MarketAnalysisOutput):
        rows = analysis.layer_results
    else:
        rows = list(analysis.get("layer_results") or [])

    by_name: dict[str, Any] = {}
    for row in rows:
        name = row.layer if isinstance(row, LayerResult) else str(row.get("layer") or "")
        if name:
            by_name[name] = row

    scores: dict[str, float] = {}
    for name in LAYER_NAMES:
        if name in by_name:
            scores[name] = layer_score_from_result(by_name[name])
        else:
            scores[name] = 0.0  # missing layer → neutral, not fabricated bullish/bearish
    return scores


def layer_score_details(scores: dict[str, float]) -> dict[str, dict[str, Any]]:
    return {k: {"score": v, "interpretation": interpret_layer_score(v)} for k, v in scores.items()}


def _signed(signal: str, confidence: float) -> float:
    c = max(0.0, min(100.0, confidence)) / 100.0
    if signal in (SignalBias.BULLISH.value, "bullish"):
        return c
    if signal in (SignalBias.SLIGHTLY_BULLISH.value, "slightly_bullish"):
        return 0.5 * c
    if signal in (SignalBias.BEARISH.value, "bearish"):
        return -c
    if signal in (SignalBias.SLIGHTLY_BEARISH.value, "slightly_bearish"):
        return -0.5 * c
    return 0.0
