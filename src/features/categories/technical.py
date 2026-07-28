"""Technical features (Ch.13 §13.8)."""

from __future__ import annotations

from typing import Any

from src.analysis import indicators as ind
from src.features.categories._util import feat, last, slope
from src.features.contracts import FeatureCategory, FeatureRecord, FeatureScale
from src.features.normalize import clamp, normalize_directional, normalize_probability


def compute_technical_features(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    *,
    asset: str = "BTCUSDT",
    timeframe: str = "1h",
) -> dict[str, FeatureRecord]:
    cat = FeatureCategory.TECHNICAL
    out: dict[str, FeatureRecord] = {}
    if len(closes) < 30:
        for name in (
            "rsi_slope",
            "macd_histogram_change",
            "adx_trend_quality",
            "bollinger_compression_ratio",
            "ema_alignment",
            "ichimoku_confirmation",
            "supertrend_direction",
            "technical_strength",
            "momentum_state",
            "breakout_readiness",
        ):
            out[name] = feat(name, None, cat, asset=asset, timeframe=timeframe, parents=["ohlcv"], source="indicators")
        return out

    rsi_s = ind.rsi(closes, 14)
    rsi_slope = slope(rsi_s, 5)
    macd_line, signal, hist = ind.macd(closes)
    hist_change = None
    h1, h0 = last(hist), None
    # previous hist
    compact = [x for x in hist if x is not None]
    if len(compact) >= 2:
        hist_change = compact[-1] - compact[-2]

    adx_s = ind.adx(highs, lows, closes, 14)
    adx_v = last(adx_s)
    mid, upper, lower, _width = ind.bollinger(closes, 20, 2.0)
    bb_u, bb_l, mid_v = last(upper), last(lower), last(mid)
    compression = None
    if bb_u is not None and bb_l is not None and mid_v:
        compression = (bb_u - bb_l) / mid_v

    e20 = last(ind.ema(closes, 20))
    e50 = last(ind.ema(closes, 50))
    e100 = last(ind.ema(closes, 100)) if len(closes) >= 100 else e50
    alignment = None
    if e20 is not None and e50 is not None and e100 is not None:
        if e20 > e50 > e100:
            alignment = 1.0
        elif e20 < e50 < e100:
            alignment = -1.0
        else:
            alignment = 0.0

    # Lightweight Ichimoku confirmation: close vs mid of recent high/low window
    window = closes[-26:] if len(closes) >= 26 else closes
    span = (max(window) + min(window)) / 2 if window else None
    ichimoku = None
    if span is not None and closes:
        ichimoku = 1.0 if closes[-1] > span else (-1.0 if closes[-1] < span else 0.0)

    # SuperTrend-like direction via ATR bands
    atr_v = last(ind.atr(highs, lows, closes, 10))
    supertrend = None
    if atr_v is not None and closes and e20 is not None:
        if closes[-1] > e20 + atr_v:
            supertrend = 1.0
        elif closes[-1] < e20 - atr_v:
            supertrend = -1.0
        else:
            supertrend = 0.0

    tech_strength = None
    parts = [p for p in (alignment, ichimoku, supertrend) if p is not None]
    if parts:
        tech_strength = normalize_directional(sum(parts) / len(parts), scale=1.0)

    momentum = None
    rv = last(rsi_s)
    if rv is not None:
        momentum = "bullish" if rv >= 55 else ("bearish" if rv <= 45 else "neutral")

    breakout = None
    if compression is not None and hist_change is not None:
        breakout = normalize_probability((1.0 - clamp(compression / 0.1, 0, 1)) * 60 + (50 if hist_change > 0 else 30))

    def add(name: str, value: Any, scale: FeatureScale = FeatureScale.RAW, parents: list[str] | None = None) -> None:
        out[name] = feat(
            name,
            None if value is None else (value if isinstance(value, str) else round(float(value), 8)),
            cat,
            scale=scale,
            asset=asset,
            timeframe=timeframe,
            parents=parents or ["indicators"],
            source="indicators",
        )

    add("rsi_slope", rsi_slope, FeatureScale.RAW, ["rsi"])
    add("macd_histogram_change", hist_change, FeatureScale.RAW, ["macd"])
    add("adx_trend_quality", adx_v, FeatureScale.PROBABILITY if adx_v and adx_v > 1 else FeatureScale.RAW, ["adx"])
    add("bollinger_compression_ratio", compression, FeatureScale.RATIO, ["bollinger"])
    add("ema_alignment", alignment, FeatureScale.DIRECTIONAL, ["ema20", "ema50", "ema100"])
    add("ichimoku_confirmation", ichimoku, FeatureScale.DIRECTIONAL, ["close"])
    add("supertrend_direction", supertrend, FeatureScale.DIRECTIONAL, ["atr", "ema"])
    add("technical_strength", tech_strength, FeatureScale.DIRECTIONAL, ["ema_alignment", "supertrend_direction"])
    add("momentum_state", momentum, FeatureScale.CATEGORICAL, ["rsi"])
    add("breakout_readiness", breakout, FeatureScale.PROBABILITY, ["bollinger_compression_ratio", "macd"])
    _ = h1
    return out
