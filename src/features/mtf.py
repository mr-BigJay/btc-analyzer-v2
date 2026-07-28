"""Multi-timeframe feature synchronization (Ch.13 §13.12)."""

from __future__ import annotations

from typing import Any, Callable

from src.features.contracts import TIMEFRAMES, FeatureSet


def synchronize_timeframes(
    compute_fn: Callable[[str], FeatureSet],
    timeframes: tuple[str, ...] = TIMEFRAMES,
) -> dict[str, Any]:
    """Compute independently per timeframe, then detect agreement on key outputs."""
    sets: dict[str, FeatureSet] = {}
    for tf in timeframes:
        sets[tf] = compute_fn(tf)

    keys = ("price_strength", "market_pressure_index", "technical_strength", "trend_integrity")
    agreement: dict[str, Any] = {}
    for key in keys:
        vals = []
        for tf, fs in sets.items():
            v = fs.get(key)
            if v is None and key in fs.composites:
                v = fs.composites.get(key)
            if v is None and key in fs.outputs:
                v = fs.outputs.get(key)
            if isinstance(v, (int, float)):
                vals.append(float(v))
        if not vals:
            agreement[key] = {"agreement": None, "mean": None, "sign_consensus": 0.0}
            continue
        signs = [1 if v > 5 else (-1 if v < -5 else 0) for v in vals]
        consensus = abs(sum(signs)) / len(signs)
        agreement[key] = {
            "agreement": consensus >= 0.6,
            "mean": round(sum(vals) / len(vals), 4),
            "sign_consensus": round(consensus, 3),
            "n": len(vals),
        }

    return {
        "timeframes": {tf: fs.to_dict() for tf, fs in sets.items()},
        "agreement": agreement,
    }
