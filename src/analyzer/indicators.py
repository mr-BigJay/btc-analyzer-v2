"""Technical indicator helpers: Bollinger, Stochastic, S/R, Fibonacci."""

from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def add_bollinger(df: pd.DataFrame, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    bb = ta.bbands(df["close"], length=length, std=std)
    if bb is not None:
        df = pd.concat([df, bb], axis=1)
    return df


def add_stochastic(df: pd.DataFrame, k: int = 14, d: int = 3) -> pd.DataFrame:
    stoch = ta.stoch(df["high"], df["low"], df["close"], k=k, d=d)
    if stoch is not None:
        df = pd.concat([df, stoch], axis=1)
    return df


def bollinger_signal(latest: pd.Series, df: pd.DataFrame) -> dict:
    """Return Bollinger band context and a 0-100 score contribution."""
    bbl = [c for c in df.columns if c.startswith("BBL_")]
    bbm = [c for c in df.columns if c.startswith("BBM_")]
    bbu = [c for c in df.columns if c.startswith("BBU_")]
    if not (bbl and bbm and bbu):
        return {"score_delta": 0, "signal": "unavailable"}

    lower, mid, upper = latest[bbl[0]], latest[bbm[0]], latest[bbu[0]]
    price = latest["close"]
    if pd.isna(lower) or pd.isna(upper) or upper == lower:
        return {"score_delta": 0, "signal": "unavailable"}

    pct_b = (price - lower) / (upper - lower)
    width = (upper - lower) / mid * 100 if mid else 0

    score_delta = 0.0
    if pct_b < 0.2:
        score_delta = 15
        signal = "near_lower_band"
    elif pct_b > 0.8:
        score_delta = -15
        signal = "near_upper_band"
    elif price > mid:
        score_delta = 5
        signal = "above_mid"
    else:
        score_delta = -5
        signal = "below_mid"

    return {
        "score_delta": score_delta,
        "signal": signal,
        "pct_b": round(float(pct_b), 3),
        "bb_lower": round(float(lower), 2),
        "bb_mid": round(float(mid), 2),
        "bb_upper": round(float(upper), 2),
        "bb_width_pct": round(float(width), 2),
    }


def stochastic_signal(latest: pd.Series, prev: pd.Series, df: pd.DataFrame) -> dict:
    k_cols = [c for c in df.columns if c.startswith("STOCHk_")]
    d_cols = [c for c in df.columns if c.startswith("STOCHd_")]
    if not k_cols:
        return {"score_delta": 0, "signal": "unavailable"}

    k_val = latest[k_cols[0]]
    d_val = latest[d_cols[0]] if d_cols else None
    if pd.isna(k_val):
        return {"score_delta": 0, "signal": "unavailable"}

    score_delta = 0.0
    if k_val < 20:
        score_delta = 12
        signal = "oversold"
    elif k_val > 80:
        score_delta = -12
        signal = "overbought"
    elif k_val > 50:
        score_delta = 5
        signal = "bullish"
    else:
        score_delta = -5
        signal = "bearish"

    crossover = None
    if d_val is not None and not pd.isna(d_val) and not pd.isna(prev.get(k_cols[0])):
        prev_k = prev[k_cols[0]]
        prev_d = prev[d_cols[0]] if d_cols else None
        if prev_d is not None and not pd.isna(prev_d):
            if prev_k <= prev_d and k_val > d_val:
                crossover = "bullish_cross"
                score_delta += 8
            elif prev_k >= prev_d and k_val < d_val:
                crossover = "bearish_cross"
                score_delta -= 8

    return {
        "score_delta": score_delta,
        "signal": signal,
        "stoch_k": round(float(k_val), 2),
        "stoch_d": round(float(d_val), 2) if d_val is not None and not pd.isna(d_val) else None,
        "crossover": crossover,
    }


def find_support_resistance(
    df: pd.DataFrame,
    lookback: int = 50,
    zone_pct: float = 0.005,
) -> dict:
    """Detect support/resistance from local extrema clustering."""
    if len(df) < 10:
        return {"support": None, "resistance": None, "signal": "insufficient_data"}

    recent = df.tail(lookback)
    highs = recent["high"].values
    lows = recent["low"].values
    price = float(recent["close"].iloc[-1])

    pivot_highs: list[float] = []
    pivot_lows: list[float] = []

    for i in range(2, len(recent) - 2):
        if highs[i] > highs[i - 1] and highs[i] > highs[i - 2] and highs[i] > highs[i + 1] and highs[i] > highs[i + 2]:
            pivot_highs.append(float(highs[i]))
        if lows[i] < lows[i - 1] and lows[i] < lows[i - 2] and lows[i] < lows[i + 1] and lows[i] < lows[i + 2]:
            pivot_lows.append(float(lows[i]))

    def _cluster(levels: list[float]) -> list[float]:
        if not levels:
            return []
        levels = sorted(levels)
        clusters: list[list[float]] = [[levels[0]]]
        for lvl in levels[1:]:
            if abs(lvl - clusters[-1][-1]) / clusters[-1][-1] <= zone_pct:
                clusters[-1].append(lvl)
            else:
                clusters.append([lvl])
        return [sum(c) / len(c) for c in clusters]

    resistances = sorted([r for r in _cluster(pivot_highs) if r > price])
    supports = sorted([s for s in _cluster(pivot_lows) if s < price], reverse=True)

    support = supports[0] if supports else float(recent["low"].min())
    resistance = resistances[0] if resistances else float(recent["high"].max())

    dist_support = (price - support) / price * 100 if support else None
    dist_resistance = (resistance - price) / price * 100 if resistance else None

    score_delta = 0.0
    signal = "mid_range"
    if dist_support is not None and dist_support < 1.5:
        score_delta = 10
        signal = "near_support"
    elif dist_resistance is not None and dist_resistance < 1.5:
        score_delta = -10
        signal = "near_resistance"

    return {
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "dist_support_pct": round(dist_support, 2) if dist_support is not None else None,
        "dist_resistance_pct": round(dist_resistance, 2) if dist_resistance is not None else None,
        "score_delta": score_delta,
        "signal": signal,
    }


def fibonacci_levels(df: pd.DataFrame, lookback: int = 100) -> dict:
    """Calculate Fibonacci retracement from recent swing high/low."""
    if len(df) < 20:
        return {"levels": {}, "signal": "insufficient_data", "score_delta": 0}

    recent = df.tail(lookback)
    swing_high = float(recent["high"].max())
    swing_low = float(recent["low"].min())
    price = float(recent["close"].iloc[-1])

    if swing_high == swing_low:
        return {"levels": {}, "signal": "flat", "score_delta": 0}

    diff = swing_high - swing_low
    ratios = {
        "0.236": swing_high - diff * 0.236,
        "0.382": swing_high - diff * 0.382,
        "0.500": swing_high - diff * 0.500,
        "0.618": swing_high - diff * 0.618,
        "0.786": swing_high - diff * 0.786,
    }
    levels = {k: round(v, 2) for k, v in ratios.items()}

    trend_up = price > (swing_low + swing_high) / 2
    nearest_level = min(levels.items(), key=lambda x: abs(price - x[1]))

    score_delta = 0.0
    signal = "between_levels"
    if trend_up and nearest_level[0] in ("0.618", "0.786") and abs(price - nearest_level[1]) / price < 0.02:
        score_delta = 8
        signal = "fib_support_in_uptrend"
    elif not trend_up and nearest_level[0] in ("0.236", "0.382") and abs(price - nearest_level[1]) / price < 0.02:
        score_delta = -8
        signal = "fib_resistance_in_downtrend"
    elif nearest_level[0] == "0.500":
        signal = "at_equilibrium"

    return {
        "swing_high": round(swing_high, 2),
        "swing_low": round(swing_low, 2),
        "levels": levels,
        "nearest_level": nearest_level[0],
        "nearest_price": nearest_level[1],
        "score_delta": score_delta,
        "signal": signal,
    }
