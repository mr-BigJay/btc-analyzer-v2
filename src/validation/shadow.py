"""Shadow mode — compare candidate engine vs production (Ch.14 §14.4 / §14.20)."""

from __future__ import annotations

from typing import Any, Callable

from src.validation.metrics import aggregate_outcome_metrics


def compare_engines(
    production_outcomes: list[dict[str, Any]],
    candidate_outcomes: list[dict[str, Any]],
    *,
    horizon: str = "24h",
) -> dict[str, Any]:
    prod = aggregate_outcome_metrics(production_outcomes, horizon=horizon)
    cand = aggregate_outcome_metrics(candidate_outcomes, horizon=horizon)
    delta = {
        "accuracy": round((cand.get("accuracy") or 0) - (prod.get("accuracy") or 0), 2),
        "f1_score": round((cand.get("f1_score") or 0) - (prod.get("f1_score") or 0), 2),
    }
    meaningful = delta["accuracy"] >= 3.0 and (cand.get("sample_size") or 0) >= 20
    return {
        "production": prod,
        "candidate": cand,
        "delta": delta,
        "statistically_meaningful_improvement": meaningful,
        "promotion_recommended": meaningful,
    }


def shadow_run(
    production_fn: Callable[[], dict[str, Any]],
    candidate_fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Execute both predictors on the same frozen inputs; caller supplies closures."""
    prod = production_fn()
    cand = candidate_fn()
    return {
        "production": prod,
        "candidate": cand,
        "agreement": {
            "bias": prod.get("market_bias") == cand.get("market_bias"),
            "confidence_delta": round(
                float(cand.get("confidence") or 0) - float(prod.get("confidence") or 0), 2
            ),
        },
    }
