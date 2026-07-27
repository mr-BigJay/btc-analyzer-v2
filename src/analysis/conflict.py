"""Conflict resolution (Ch.6 §6.7)."""

from __future__ import annotations

from dataclasses import dataclass

from src.analysis.contracts import LayerResult, SignalBias


@dataclass
class ConflictResolution:
    market_bias: str
    confidence: float
    conflicts: list[str]
    mixed: bool


def resolve_conflicts(
    layer_results: list[LayerResult],
    weights: dict[str, float],
) -> ConflictResolution:
    """Weighted synthesis — not a blind average (Ch.6 §6.7)."""
    bull_cluster = []
    bear_cluster = []
    neutral_cluster = []
    weighted = 0.0
    weight_sum = 0.0
    reliability_sum = 0.0

    for r in layer_results:
        w = weights.get(r.layer, 0.05) * max(0.2, r.data_quality)
        signed = r.signed_score
        weighted += signed * w
        weight_sum += w
        reliability_sum += (r.confidence / 100.0) * w

        if signed > 0.15:
            bull_cluster.append(r.layer)
        elif signed < -0.15:
            bear_cluster.append(r.layer)
        else:
            neutral_cluster.append(r.layer)

    score = weighted / weight_sum if weight_sum else 0.0
    conflicts: list[str] = []
    mixed = False
    if bull_cluster and bear_cluster:
        mixed = True
        conflicts.append(
            f"Contradictory clusters: bullish={bull_cluster} bearish={bear_cluster}"
        )

    # Map score → bias labels from Ch.6
    abs_score = abs(score)
    if mixed and abs_score < 0.25:
        bias = SignalBias.HIGH_UNCERTAINTY.value
        conf = max(25.0, 55.0 - len(conflicts) * 8)
    elif score >= 0.45:
        bias = SignalBias.BULLISH.value
        conf = 55 + abs_score * 40
    elif score >= 0.18:
        bias = SignalBias.SLIGHTLY_BULLISH.value
        conf = 50 + abs_score * 35
    elif score <= -0.45:
        bias = SignalBias.BEARISH.value
        conf = 55 + abs_score * 40
    elif score <= -0.18:
        bias = SignalBias.SLIGHTLY_BEARISH.value
        conf = 50 + abs_score * 35
    else:
        bias = SignalBias.NEUTRAL.value
        conf = 45 + (1 - abs_score) * 10

    # Reduce confidence when mixed
    if mixed:
        conf *= 0.75
        conflicts.append("Mixed-market conditions — confidence reduced")

    # Blend in average layer reliability
    if weight_sum:
        conf = 0.7 * conf + 0.3 * (reliability_sum / weight_sum) * 100

    return ConflictResolution(
        market_bias=bias,
        confidence=max(0.0, min(100.0, conf)),
        conflicts=conflicts,
        mixed=mixed,
    )
