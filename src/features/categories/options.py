"""Options features (Ch.13 §13.7)."""

from __future__ import annotations

from typing import Any

from src.features.categories._util import feat, safe_div
from src.features.contracts import FeatureCategory, FeatureRecord, FeatureScale
from src.features.normalize import clamp, normalize_directional, normalize_probability


def compute_options_features(
    *,
    put_call_ratio: float | None = None,
    pcr_prev: float | None = None,
    iv: float | None = None,
    iv_prev: float | None = None,
    iv_rank: float | None = None,
    iv_percentile: float | None = None,
    gamma_exposure: float | None = None,
    dealer_gamma: float | None = None,
    dealer_delta: float | None = None,
    max_pain: float | None = None,
    spot: float | None = None,
    asset: str = "BTCUSDT",
    timeframe: str = "1h",
) -> dict[str, FeatureRecord]:
    cat = FeatureCategory.OPTIONS
    out: dict[str, FeatureRecord] = {}

    pcr_trend = None
    if put_call_ratio is not None and pcr_prev is not None:
        pcr_trend = put_call_ratio - pcr_prev
    elif put_call_ratio is not None:
        pcr_trend = put_call_ratio - 1.0

    pcr_div = None
    if put_call_ratio is not None and spot is not None and max_pain is not None and max_pain != 0:
        # PCR vs distance-to-max-pain disagreement proxy
        dist = (spot - max_pain) / max_pain
        pcr_div = put_call_ratio - 1.0 - dist

    iv_change = None
    if iv is not None and iv_prev is not None:
        iv_change = iv - iv_prev

    gamma_shift = dealer_gamma if dealer_gamma is not None else gamma_exposure
    max_pain_dist = safe_div((spot - max_pain) if spot is not None and max_pain is not None else None, spot)

    dealer_bias = None
    if dealer_gamma is not None:
        dealer_bias = normalize_directional(clamp(dealer_gamma, -1e9, 1e9) / 1e8, scale=1.0)
    elif put_call_ratio is not None:
        dealer_bias = normalize_directional(1.0 - put_call_ratio, scale=1.0)

    hedging = None
    if gamma_shift is not None:
        hedging = normalize_probability(min(100.0, abs(float(gamma_shift)) / 1e7 * 50))
    elif dealer_delta is not None:
        hedging = normalize_probability(min(100.0, abs(dealer_delta) * 50))

    sentiment = None
    if put_call_ratio is not None:
        # PCR > 1 often defensive; invert for bullish sentiment
        sentiment = normalize_directional(1.0 - put_call_ratio, scale=1.0)

    def add(name: str, value: Any, scale: FeatureScale = FeatureScale.RAW, parents: list[str] | None = None) -> None:
        out[name] = feat(
            name,
            None if value is None else round(float(value), 8),
            cat,
            scale=scale,
            asset=asset,
            timeframe=timeframe,
            parents=parents or [],
            source="Options API",
        )

    add("pcr_trend", pcr_trend, FeatureScale.RAW, ["put_call_ratio"])
    add("pcr_divergence", pcr_div, FeatureScale.RAW, ["put_call_ratio", "max_pain", "spot"])
    add("iv_change", iv_change, FeatureScale.RAW, ["iv"])
    add("iv_rank", iv_rank, FeatureScale.PROBABILITY if iv_rank is not None and iv_rank > 1 else FeatureScale.RATIO, ["iv"])
    add("iv_percentile", iv_percentile, FeatureScale.PROBABILITY if iv_percentile is not None and iv_percentile > 1 else FeatureScale.RATIO, ["iv"])
    add("gamma_shift", gamma_shift, FeatureScale.RAW, ["gamma_exposure", "dealer_gamma"])
    add("dealer_exposure", dealer_delta if dealer_delta is not None else dealer_gamma, FeatureScale.RAW, ["dealer_delta", "dealer_gamma"])
    add("max_pain_distance", max_pain_dist, FeatureScale.RAW, ["max_pain", "spot"])
    add("dealer_bias", dealer_bias, FeatureScale.DIRECTIONAL, ["dealer_gamma", "put_call_ratio"])
    add("hedging_pressure", hedging, FeatureScale.PROBABILITY, ["gamma_shift"])
    add("options_sentiment", sentiment, FeatureScale.DIRECTIONAL, ["put_call_ratio"])
    return out
