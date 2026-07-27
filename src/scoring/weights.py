"""Dynamic layer weights by market regime (Ch.9 §9.6)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

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

TREND_WEIGHTS: dict[str, float] = {
    "Spot": 0.22,
    "Futures": 0.23,
    "Options": 0.18,
    "Technical": 0.17,
    "Market Structure": 0.12,
    "Liquidity": 0.05,
    "Pattern Detection": 0.02,
    "Volatility": 0.01,
}

RANGE_WEIGHTS: dict[str, float] = {
    "Spot": 0.15,
    "Futures": 0.15,
    "Options": 0.25,
    "Technical": 0.15,
    "Market Structure": 0.08,
    "Liquidity": 0.12,
    "Pattern Detection": 0.07,
    "Volatility": 0.03,
}

HIGH_VOL_WEIGHTS: dict[str, float] = {
    "Spot": 0.18,
    "Futures": 0.18,
    "Options": 0.22,
    "Technical": 0.10,
    "Market Structure": 0.08,
    "Liquidity": 0.08,
    "Pattern Detection": 0.03,
    "Volatility": 0.13,
}


def resolve_weight_regime(
    *,
    market_regime: str | None = None,
    volatility_regime: str | None = None,
    analysis_regime: str | None = None,
) -> str:
    vol = (volatility_regime or "").lower()
    if vol in ("elevated", "extreme", "high") or "expansion" in (market_regime or "").lower():
        return "high_volatility"

    regime = (market_regime or analysis_regime or "").lower()
    if any(k in regime for k in ("uptrend", "downtrend", "trend", "markup", "markdown")):
        return "trend"
    if any(k in regime for k in ("range", "compression", "accumulation")):
        return "range"
    return "default"


def weights_for_regime(regime_key: str) -> dict[str, float]:
    table = {
        "trend": TREND_WEIGHTS,
        "range": RANGE_WEIGHTS,
        "high_volatility": HIGH_VOL_WEIGHTS,
        "default": DEFAULT_WEIGHTS,
    }.get(regime_key, DEFAULT_WEIGHTS)
    return deepcopy(table)


def apply_quality_adjustments(
    weights: dict[str, float],
    *,
    layer_scores: dict[str, float],
    layer_results: list[dict[str, Any]] | None = None,
    near_options_expiry: bool = False,
) -> dict[str, float]:
    """Down-weight low-quality / missing layers; optional expiry boost (still sums to 1)."""
    w = deepcopy(weights)
    quality = {}
    for row in layer_results or []:
        quality[str(row.get("layer"))] = float(row.get("data_quality") if row.get("data_quality") is not None else 1.0)

    for layer in list(w.keys()):
        dq = quality.get(layer, 1.0 if layer in layer_scores else 0.3)
        if dq < 0.45:
            w[layer] *= 0.4
        elif layer not in layer_scores:
            w[layer] *= 0.3

    if near_options_expiry:
        w["Options"] = min(0.35, w["Options"] + 0.05)
        w["Technical"] = max(0.05, w["Technical"] - 0.025)
        w["Spot"] = max(0.10, w["Spot"] - 0.025)

    total = sum(w.values()) or 1.0
    return {k: round(v / total, 6) for k, v in w.items()}


def select_weights(
    *,
    market_regime: str | None = None,
    volatility_regime: str | None = None,
    analysis_regime: str | None = None,
    layer_scores: dict[str, float] | None = None,
    layer_results: list[dict[str, Any]] | None = None,
    near_options_expiry: bool = False,
) -> tuple[dict[str, float], str]:
    key = resolve_weight_regime(
        market_regime=market_regime,
        volatility_regime=volatility_regime,
        analysis_regime=analysis_regime,
    )
    weights = weights_for_regime(key)
    weights = apply_quality_adjustments(
        weights,
        layer_scores=layer_scores or {},
        layer_results=layer_results,
        near_options_expiry=near_options_expiry,
    )
    return weights, key
