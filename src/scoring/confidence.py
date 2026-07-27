"""Confidence calibration, conflict penalties, MTF consensus (Ch.9 §9.10 / §9.12 / §9.13)."""

from __future__ import annotations

from typing import Any

from src.scoring.contracts import AlignmentClass

# Conflict penalties (Ch.9 §9.13) — applied to confidence, not direction (unless extreme)
CONFLICT_PENALTIES: list[tuple[str, str, float]] = [
    ("Spot", "Futures", -5.0),
    ("Futures", "Options", -4.0),
    ("Technical", "Market Structure", -3.0),
]

MTF_WEIGHTS: dict[str, float] = {
    "5m": 0.10,
    "15m": 0.15,
    "1h": 0.25,
    "4h": 0.30,
    "1d": 0.20,
}


def layer_agreement(layer_scores: dict[str, float], *, threshold: float = 15.0) -> tuple[float, str]:
    """Return (agreement 0–1, band label for confidence tables)."""
    vals = list(layer_scores.values())
    if not vals:
        return 0.0, "Significant conflict"
    bull = sum(1 for v in vals if v >= threshold)
    bear = sum(1 for v in vals if v <= -threshold)
    neutral = len(vals) - bull - bear
    directional = bull + bear
    if directional == 0:
        return 0.55, "Mixed signals"
    majority = max(bull, bear) / max(1, len(vals))
    if majority >= 0.85 and min(bull, bear) == 0:
        return majority, "All layers aligned"
    if majority >= 0.65 and min(bull, bear) <= 1:
        return majority, "Minor disagreement"
    if majority >= 0.45:
        return majority, "Mixed signals"
    return majority, "Significant conflict"


def conflict_penalties(layer_scores: dict[str, float], *, threshold: float = 25.0) -> tuple[float, list[dict[str, Any]]]:
    """Sum confidence penalties from opposing layer pairs."""
    details: list[dict[str, Any]] = []
    total = 0.0
    for a, b, penalty in CONFLICT_PENALTIES:
        sa = layer_scores.get(a)
        sb = layer_scores.get(b)
        if sa is None or sb is None:
            continue
        if (sa >= threshold and sb <= -threshold) or (sa <= -threshold and sb >= threshold):
            total += penalty
            details.append({"pair": f"{a} vs {b}", "penalty": penalty, "scores": {a: sa, b: sb}})

    # Multi-layer contradiction
    bull = sum(1 for v in layer_scores.values() if v >= threshold)
    bear = sum(1 for v in layer_scores.values() if v <= -threshold)
    if bull >= 2 and bear >= 2:
        total += -10.0
        details.append({"pair": "multi-layer contradiction", "penalty": -10.0, "bull_layers": bull, "bear_layers": bear})

    return total, details


def timeframe_consensus(timeframe_alignment: dict[str, Any] | None) -> tuple[str, float]:
    """
    Classify MTF alignment (Ch.9 §9.12).
    Returns (alignment_class, confidence_delta).
    """
    mtf = timeframe_alignment or {}
    biases = mtf.get("biases") or {}
    if not biases:
        if mtf.get("aligned"):
            return AlignmentClass.FULL.value, 6.0
        if mtf.get("divergent"):
            return AlignmentClass.DIVERGENCE.value, -12.0
        return AlignmentClass.PARTIAL.value, 0.0

    values = list(biases.values())
    unique = {str(v) for v in values}
    if len(values) >= 2 and len(unique) == 1:
        return AlignmentClass.FULL.value, 8.0
    if len(unique) == 2:
        return AlignmentClass.PARTIAL.value, 2.0
    if len(unique) >= 3:
        return AlignmentClass.DIVERGENCE.value, -12.0
    return AlignmentClass.MIXED.value, -6.0


def calibrate_confidence_score(
    *,
    layer_scores: dict[str, float],
    analysis: dict[str, Any],
    intelligence: dict[str, Any] | None = None,
    data_quality_score: float = 80.0,
    near_macro: bool = False,
) -> tuple[float, str, list[dict[str, Any]], dict[str, Any]]:
    """Confidence Score 0–100 (Ch.9 §9.10)."""
    intel = intelligence or {}
    agreement, agreement_label = layer_agreement(layer_scores)
    penalty_sum, penalties = conflict_penalties(layer_scores)
    alignment, mtf_delta = timeframe_consensus(analysis.get("timeframe_alignment"))

    # Base from agreement bands (Ch.9 example table)
    if agreement_label == "All layers aligned":
        base = 92.0
    elif agreement_label == "Minor disagreement":
        base = 80.0
    elif agreement_label == "Mixed signals":
        base = 67.0
    else:
        base = 52.0

    # Blend with analysis confidence + DQS + regime stability
    analysis_conf = float(analysis.get("confidence") or 50)
    conf = 0.45 * base + 0.25 * analysis_conf + 0.20 * float(data_quality_score) + 0.10 * (agreement * 100)
    conf += mtf_delta
    conf += penalty_sum

    # Regime stability
    transition = float(intel.get("transition_probability") or 0)
    if transition >= 55:
        conf -= 8
    elif transition <= 20:
        conf += 2

    if near_macro or intel.get("macro_bias") in ("Cautious", "Uncertain", "Risk-Off"):
        conf -= 5

    completeness = float(intel.get("data_completeness") or analysis.get("data_completeness") or 1.0)
    conf *= 0.85 + 0.15 * max(0.2, min(1.0, completeness))

    conf = max(0.0, min(100.0, conf))
    meta = {
        "agreement": round(agreement, 3),
        "agreement_label": agreement_label,
        "mtf_alignment": alignment,
        "mtf_delta": mtf_delta,
        "penalty_sum": penalty_sum,
    }
    return round(conf, 1), alignment, penalties, meta
