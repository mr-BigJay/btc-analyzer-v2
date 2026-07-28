"""Price features (Ch.13 §13.4)."""

from __future__ import annotations

from typing import Any

from src.analysis import indicators as ind
from src.features.categories._util import feat, last, log_return, pct_return, safe_div, slope
from src.features.contracts import FeatureCategory, FeatureRecord, FeatureScale
from src.features.normalize import normalize_directional


def compute_price_features(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    *,
    volumes: list[float] | None = None,
    asset: str = "BTCUSDT",
    timeframe: str = "1h",
    vwap: float | None = None,
) -> dict[str, FeatureRecord]:
    cat = FeatureCategory.PRICE
    n = len(closes)
    out: dict[str, FeatureRecord] = {}
    c = closes[-1] if closes else None
    prev = closes[-2] if n >= 2 else None

    lr = log_return(c, prev)
    pr = pct_return(c, prev)
    roll = pct_return(c, closes[-6]) if n >= 6 else None

    emas = ind.ema(closes, 20) if closes else []
    ema20 = last(emas)
    atrs = ind.atr(highs, lows, closes, 14) if closes and highs and lows else []
    atr_v = last(atrs)

    # VWAP approximation from closes/volumes if not provided
    if vwap is None and volumes and closes and len(volumes) == len(closes):
        num = sum(closes[i] * volumes[i] for i in range(len(closes)))
        den = sum(volumes) or 1.0
        vwap = num / den

    dist_vwap = safe_div((c - vwap) if c is not None and vwap is not None else None, vwap)
    dist_ema = safe_div((c - ema20) if c is not None and ema20 is not None else None, ema20)
    atr_ratio = safe_div(atr_v, c)

    body = None
    upper_wick = None
    lower_wick = None
    if n >= 1 and highs and lows:
        # Use last candle OHLC if available via highs/lows/closes only — open≈prev close
        o = prev if prev is not None else c
        h = highs[-1] if highs else c
        low = lows[-1] if lows else c
        if o is not None and c is not None and h is not None and low is not None and h != low:
            body = abs(c - o) / (h - low)
            upper_wick = (h - max(o, c)) / (h - low)
            lower_wick = (min(o, c) - low) / (h - low)

    vel = slope(closes, 5)
    # Acceleration = slope of recent returns
    rets = []
    for i in range(1, min(8, n)):
        r = pct_return(closes[-i], closes[-i - 1]) if n > i else None
        if r is not None:
            rets.append(r)
    accel = slope(list(reversed(rets)), 4) if len(rets) >= 2 else None

    price_strength = normalize_directional(pr, scale=0.02) if pr is not None else None
    trend_velocity = normalize_directional(vel, scale=(c * 0.01 if c else 1.0)) if vel is not None else None
    price_acceleration = normalize_directional(accel, scale=0.005) if accel is not None else None

    def add(name: str, value: Any, scale: FeatureScale = FeatureScale.RAW, parents: list[str] | None = None) -> None:
        out[name] = feat(
            name,
            None if value is None else (round(float(value), 8) if not isinstance(value, str) else value),
            cat,
            scale=scale,
            asset=asset,
            timeframe=timeframe,
            parents=parents or ["close"],
            source="OHLCV",
        )

    add("log_return", lr, FeatureScale.RAW, ["close"])
    add("pct_return", pr, FeatureScale.RAW, ["close"])
    add("rolling_return", roll, FeatureScale.RAW, ["close"])
    add("distance_from_vwap", dist_vwap, FeatureScale.RAW, ["close", "vwap"])
    add("distance_from_ema", dist_ema, FeatureScale.RAW, ["close", "ema20"])
    add("atr_ratio", atr_ratio, FeatureScale.RATIO, ["atr", "close"])
    add("candle_body_ratio", body, FeatureScale.RATIO, ["open", "high", "low", "close"])
    add("upper_wick_ratio", upper_wick, FeatureScale.RATIO, ["open", "high", "close"])
    add("lower_wick_ratio", lower_wick, FeatureScale.RATIO, ["open", "low", "close"])
    add("price_strength", price_strength, FeatureScale.DIRECTIONAL, ["pct_return"])
    add("trend_velocity", trend_velocity, FeatureScale.DIRECTIONAL, ["close"])
    add("price_acceleration", price_acceleration, FeatureScale.DIRECTIONAL, ["pct_return"])
    return out
