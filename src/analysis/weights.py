"""Dynamic layer weights (Ch.6 §6.8 / Ch.9 §9.6).

Ch.9 regime tables are canonical; this module remains for Analysis Engine
compatibility and applies the same default/trend/range/high-vol profiles.
"""

from __future__ import annotations

from typing import Iterable

from src.analysis.contracts import LayerResult
from src.scoring.weights import (
    DEFAULT_WEIGHTS,
    HIGH_VOL_WEIGHTS,
    RANGE_WEIGHTS,
    TREND_WEIGHTS,
    select_weights,
)

__all__ = [
    "DEFAULT_WEIGHTS",
    "TREND_WEIGHTS",
    "RANGE_WEIGHTS",
    "HIGH_VOL_WEIGHTS",
    "compute_weights",
]


def compute_weights(layer_results: Iterable[LayerResult], *, near_options_expiry: bool = False) -> dict[str, float]:
    results = list(layer_results)
    tags = {t for r in results for t in r.tags}
    rows = [
        {
            "layer": r.layer,
            "data_quality": r.data_quality,
            "tags": r.tags,
        }
        for r in results
    ]

    if "Expansion" in tags or "High Volatility" in tags:
        regime, vol = "Expansion", "Elevated"
    elif "Compression" in tags:
        regime, vol = "Compression", "Low"
    elif "Trend Strength" in tags or "BOS" in tags:
        regime, vol = "Strong Uptrend", "Normal"
    else:
        regime, vol = "Range", "Normal"

    weights, _key = select_weights(
        market_regime=regime,
        volatility_regime=vol,
        layer_scores={r.layer: 0.0 for r in results},
        layer_results=rows,
        near_options_expiry=near_options_expiry or "Gamma Pinning" in tags,
    )
    return weights
