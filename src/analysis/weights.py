"""Dynamic layer weights (Ch.6 §6.8)."""

from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from src.analysis.contracts import LayerResult

DEFAULT_WEIGHTS: dict[str, float] = {
    "Spot": 0.20,
    "Futures": 0.20,
    "Options": 0.20,
    "Technical": 0.15,
    "Market Structure": 0.10,
    "Liquidity": 0.07,
    "Pattern Detection": 0.05,
    "Volatility": 0.03,
}


def compute_weights(layer_results: Iterable[LayerResult], *, near_options_expiry: bool = False) -> dict[str, float]:
    weights = deepcopy(DEFAULT_WEIGHTS)
    tags = {t for r in layer_results for t in r.tags}
    vol_tags = tags

    # Options expiry → boost Options
    if near_options_expiry or "Gamma Pinning" in tags:
        weights["Options"] = min(0.35, weights["Options"] + 0.08)
        weights["Technical"] = max(0.08, weights["Technical"] - 0.03)
        weights["Spot"] = max(0.12, weights["Spot"] - 0.03)

    # Breakout / BOS → Structure + Liquidity
    if "BOS" in tags or "Breakout Probability" in tags:
        weights["Market Structure"] = min(0.20, weights["Market Structure"] + 0.06)
        weights["Liquidity"] = min(0.14, weights["Liquidity"] + 0.04)
        weights["Pattern Detection"] = min(0.10, weights["Pattern Detection"] + 0.02)
        weights["Volatility"] = max(0.02, weights["Volatility"] - 0.01)

    # High volatility regime
    if "Expansion" in vol_tags or "High Volatility" in vol_tags:
        weights["Volatility"] = min(0.12, weights["Volatility"] + 0.06)
        weights["Futures"] = min(0.25, weights["Futures"] + 0.02)
        weights["Technical"] = max(0.10, weights["Technical"] - 0.03)

    # Down-weight low-quality layers
    for r in layer_results:
        if r.layer in weights and r.data_quality < 0.45:
            weights[r.layer] *= 0.4

    # Renormalize
    total = sum(weights.values()) or 1.0
    return {k: v / total for k, v in weights.items()}
