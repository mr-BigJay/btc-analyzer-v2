"""Data Quality Score — DQS (Ch.9 §9.14)."""

from __future__ import annotations

from typing import Any

from src.scoring.contracts import dqs_band


def compute_dqs(
    analysis: dict[str, Any],
    *,
    intelligence: dict[str, Any] | None = None,
    source_flags: dict[str, bool] | None = None,
) -> tuple[float, str, dict[str, Any]]:
    """
    Score data integrity for this analysis cycle.
    Inputs: API availability proxies, missing values, validation-ish completeness.
    """
    intel = intelligence or {}
    layers = list(analysis.get("layer_results") or [])
    expected = 8
    present = len(layers)
    coverage = present / expected

    qualities = [float(r.get("data_quality") if r.get("data_quality") is not None else 0.6) for r in layers]
    avg_q = sum(qualities) / max(1, len(qualities)) if qualities else 0.4

    # Missing summaries / empty tags aren't fatal but lower score
    missing_summary = sum(1 for r in layers if not r.get("summary"))
    freshness_penalty = 0.0
    # If analysis confidence very low with empty conflicts unexplained → possible stale
    if float(analysis.get("confidence") or 0) < 30 and not layers:
        freshness_penalty = 25.0

    flags = source_flags or {}
    if not flags and intel:
        # proxy completeness from intelligence
        pass
    live_ratio = 1.0
    if flags:
        live_ratio = sum(1 for v in flags.values() if v) / max(1, len(flags))

    completeness = float(intel.get("data_completeness") or (0.6 * coverage + 0.4 * avg_q))

    # coverage/avg_q/completeness/live_ratio are 0-1 → weighted sum is 0-100
    score = 35 * coverage + 30 * avg_q + 20 * completeness + 15 * live_ratio
    score -= missing_summary * 1.5
    score -= freshness_penalty
    if analysis.get("conflicts") and avg_q < 0.5:
        score -= 5

    score = max(0.0, min(100.0, score))
    details = {
        "layer_coverage": round(coverage, 3),
        "avg_layer_quality": round(avg_q, 3),
        "completeness": round(completeness, 3),
        "live_ratio": round(live_ratio, 3),
        "band": dqs_band(score),
    }
    return round(score, 1), dqs_band(score), details
