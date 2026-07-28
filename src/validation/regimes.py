"""Regime-based and layer contribution evaluation (Ch.14 §14.14–§14.15)."""

from __future__ import annotations

from typing import Any, Sequence


def regime_accuracy(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """rows need market_regime + direction_correct."""
    by: dict[str, list[bool]] = {}
    for r in rows:
        regime = str(r.get("market_regime") or "Unknown")
        ok = r.get("direction_correct")
        if ok is None:
            continue
        by.setdefault(regime, []).append(bool(ok))
    out = {}
    for regime, vals in by.items():
        out[regime] = {
            "n": len(vals),
            "accuracy": round(100.0 * sum(vals) / len(vals), 1) if vals else None,
        }
    return out


def layer_contribution(rows: Sequence[dict[str, Any]]) -> dict[str, str]:
    """Heuristic contribution: correlation of layer score sign with correctness."""
    # Aggregate per-layer: when |score| high and direction aligns with correctness → contribution
    stats: dict[str, list[float]] = {}
    for r in rows:
        correct = r.get("direction_correct")
        if correct is None:
            continue
        scores = r.get("layer_scores") or {}
        if not isinstance(scores, dict):
            continue
        bias = str(r.get("market_bias") or "")
        for layer, score in scores.items():
            try:
                s = float(score)
            except (TypeError, ValueError):
                continue
            # Agreement proxy
            agrees = (("bull" in bias.lower() and s > 0) or ("bear" in bias.lower() and s < 0) or abs(s) < 15)
            credit = (1.0 if (agrees and correct) or ((not agrees) and (not correct)) else 0.0)
            stats.setdefault(str(layer), []).append(credit)

    labels = {}
    for layer, vals in stats.items():
        if not vals:
            labels[layer] = "Unknown"
            continue
        rate = sum(vals) / len(vals)
        if rate >= 0.7:
            labels[layer] = "High"
        elif rate >= 0.5:
            labels[layer] = "Medium"
        else:
            labels[layer] = "Low"
    return labels
