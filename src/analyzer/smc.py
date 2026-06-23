"""Smart Money Concepts — FVG, BOS, CHoCH, Order Blocks."""

from __future__ import annotations

import pandas as pd


def detect_fvg(df: pd.DataFrame, lookback: int = 50) -> list[dict]:
    """Detect Fair Value Gaps in recent candles."""
    zones: list[dict] = []
    start = max(2, len(df) - lookback)

    for i in range(start, len(df)):
        c0 = df.iloc[i - 2]
        c2 = df.iloc[i]
        if c0["high"] < c2["low"]:
            zones.append(
                {
                    "type": "bullish_fvg",
                    "top": float(c2["low"]),
                    "bottom": float(c0["high"]),
                    "mid": float((c2["low"] + c0["high"]) / 2),
                    "index": i,
                }
            )
        elif c0["low"] > c2["high"]:
            zones.append(
                {
                    "type": "bearish_fvg",
                    "top": float(c0["low"]),
                    "bottom": float(c2["high"]),
                    "mid": float((c0["low"] + c2["high"]) / 2),
                    "index": i,
                }
            )

    return zones[-5:]


def detect_swing_points(df: pd.DataFrame, window: int = 5) -> tuple[list, list]:
    highs, lows = [], []
    for i in range(window, len(df) - window):
        h = df["high"].iloc[i]
        l = df["low"].iloc[i]
        if h == df["high"].iloc[i - window : i + window + 1].max():
            highs.append((i, float(h)))
        if l == df["low"].iloc[i - window : i + window + 1].min():
            lows.append((i, float(l)))
    return highs, lows


def detect_bos_choch(df: pd.DataFrame) -> dict:
    """Detect Break of Structure and Change of Character."""
    highs, lows = detect_swing_points(df.tail(60))
    if len(highs) < 2 or len(lows) < 2:
        return {"event": "none", "signal": "insufficient_data", "score_delta": 0}

    price = float(df["close"].iloc[-1])
    last_high = highs[-1][1]
    prev_high = highs[-2][1]
    last_low = lows[-1][1]
    prev_low = lows[-2][1]

    hh = last_high > prev_high
    hl = last_low > prev_low
    lh = last_high < prev_high
    ll = last_low < prev_low

    if hh and hl:
        return {"event": "bos_bullish", "signal": "bullish", "score_delta": 12}
    if lh and ll:
        return {"event": "bos_bearish", "signal": "bearish", "score_delta": -12}
    if lh and hl:
        return {"event": "choch_bullish", "signal": "reversal_up", "score_delta": 8}
    if hh and ll:
        return {"event": "choch_bearish", "signal": "reversal_down", "score_delta": -8}

    return {"event": "none", "signal": "neutral", "score_delta": 0}


def detect_order_blocks(df: pd.DataFrame, lookback: int = 30) -> list[dict]:
    """Simplified order blocks — last opposite candle before displacement."""
    blocks: list[dict] = []
    recent = df.tail(lookback).reset_index(drop=True)

    for i in range(2, len(recent) - 1):
        body_prev = abs(recent["close"].iloc[i - 1] - recent["open"].iloc[i - 1])
        range_i = recent["high"].iloc[i] - recent["low"].iloc[i]
        if range_i == 0:
            continue
        displacement = range_i > body_prev * 2

        if displacement and recent["close"].iloc[i] > recent["open"].iloc[i]:
            ob = recent.iloc[i - 1]
            if ob["close"] < ob["open"]:
                blocks.append(
                    {
                        "type": "bullish_ob",
                        "top": float(ob["high"]),
                        "bottom": float(ob["low"]),
                        "index": i - 1,
                    }
                )
        elif displacement and recent["close"].iloc[i] < recent["open"].iloc[i]:
            ob = recent.iloc[i - 1]
            if ob["close"] > ob["open"]:
                blocks.append(
                    {
                        "type": "bearish_ob",
                        "top": float(ob["high"]),
                        "bottom": float(ob["low"]),
                        "index": i - 1,
                    }
                )

    return blocks[-3:]


def analyze_smc(df: pd.DataFrame, price: float) -> dict:
    """Full SMC analysis for a timeframe."""
    fvg_zones = detect_fvg(df)
    bos = detect_bos_choch(df)
    order_blocks = detect_order_blocks(df)

    active_fvg = None
    for z in reversed(fvg_zones):
        if z["bottom"] <= price <= z["top"]:
            active_fvg = z
            break

    nearest_ob = None
    min_dist = float("inf")
    for ob in order_blocks:
        mid = (ob["top"] + ob["bottom"]) / 2
        dist = abs(price - mid)
        if dist < min_dist:
            min_dist = dist
            nearest_ob = ob

    score_delta = bos.get("score_delta", 0)
    if active_fvg:
        if active_fvg["type"] == "bullish_fvg":
            score_delta += 6
        else:
            score_delta -= 6

    return {
        "fvg_zones": fvg_zones,
        "active_fvg": active_fvg,
        "bos_choch": bos,
        "order_blocks": order_blocks,
        "nearest_ob": nearest_ob,
        "score_delta": score_delta,
        "signal": bos.get("event", "none"),
    }
