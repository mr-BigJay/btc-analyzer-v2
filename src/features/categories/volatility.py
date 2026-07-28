"""Volatility features (Ch.13 §13.11)."""

from __future__ import annotations

import math
from typing import Any

from src.analysis import indicators as ind
from src.features.categories._util import feat, last, safe_div
from src.features.contracts import FeatureCategory, FeatureRecord, FeatureScale
from src.features.normalize import clamp, normalize_probability


def compute_volatility_features(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    *,
    implied_volatility: float | None = None,
    asset: str = "BTCUSDT",
    timeframe: str = "1h",
) -> dict[str, FeatureRecord]:
    cat = FeatureCategory.VOLATILITY
    out: dict[str, FeatureRecord] = {}

    atr_s = ind.atr(highs, lows, closes, 14) if closes and highs and lows else []
    atr_v = last(atr_s)
    atr_pct = None
    if atr_v is not None and closes:
        # percentile vs recent ATR history
        hist = [x for x in atr_s[-50:] if x is not None]
        if hist:
            atr_pct = sum(1 for x in hist if x <= atr_v) / len(hist) * 100.0

    hv = None
    if len(closes) >= 20:
        rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
        if len(rets) >= 10:
            mean = sum(rets[-20:]) / min(20, len(rets))
            var = sum((r - mean) ** 2 for r in rets[-20:]) / max(1, min(20, len(rets)) - 1)
            hv = math.sqrt(var) * math.sqrt(365) * 100

    hv_rank = None
    if hv is not None:
        # Without long HV history, rank against a soft 20–80 band
        hv_rank = normalize_probability(clamp((hv - 20) / 60 * 100, 0, 100))

    iv_hv = safe_div(implied_volatility, hv / 100.0 if hv else None) if implied_volatility is not None else None

    mid, upper, lower, _width = ind.bollinger(closes, 20, 2.0) if len(closes) >= 20 else ([], [], [], [])
    bb_u, bb_l, mid_v = last(upper), last(lower), last(mid)
    bb_width = None
    if bb_u is not None and bb_l is not None and mid_v:
        bb_width = (bb_u - bb_l) / mid_v
    bb_score = normalize_probability(clamp((bb_width or 0) / 0.1 * 100, 0, 100)) if bb_width is not None else None

    expansion = None
    atr_hist = [x for x in atr_s[-10:] if x is not None]
    if len(atr_hist) >= 4:
        expansion = (atr_hist[-1] - atr_hist[0]) / (atr_hist[0] or 1.0)

    vol_state = None
    if atr_pct is not None:
        vol_state = "expanding" if atr_pct >= 70 else ("compressing" if atr_pct <= 30 else "normal")

    expansion_prob = normalize_probability(50 + clamp((expansion or 0) * 100, -50, 50)) if expansion is not None else None

    def add(name: str, value: Any, scale: FeatureScale = FeatureScale.RAW, parents: list[str] | None = None) -> None:
        out[name] = feat(
            name,
            None if value is None else (value if isinstance(value, str) else round(float(value), 8)),
            cat,
            scale=scale,
            asset=asset,
            timeframe=timeframe,
            parents=parents or ["ohlcv"],
            source="volatility",
        )

    add("atr_percentile", atr_pct, FeatureScale.PROBABILITY, ["atr"])
    add("historical_volatility_rank", hv_rank, FeatureScale.PROBABILITY, ["hv"])
    add("iv_hv_ratio", iv_hv, FeatureScale.RAW, ["iv", "hv"])
    add("bollinger_width_score", bb_score, FeatureScale.PROBABILITY, ["bollinger"])
    add("volatility_expansion_rate", expansion, FeatureScale.RAW, ["atr"])
    add("volatility_state", vol_state, FeatureScale.CATEGORICAL, ["atr_percentile"])
    add("expansion_probability", expansion_prob, FeatureScale.PROBABILITY, ["volatility_expansion_rate"])
    return out
