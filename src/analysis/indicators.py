"""Pure indicator helpers for Technical / Volatility layers (deterministic)."""

from __future__ import annotations

import math
from typing import Sequence


def ema(values: Sequence[float], period: int) -> list[float | None]:
    if period <= 0 or not values:
        return [None] * len(values)
    k = 2 / (period + 1)
    out: list[float | None] = [None] * len(values)
    seed = None
    acc = 0.0
    for i, v in enumerate(values):
        if i < period - 1:
            acc += v
            continue
        if i == period - 1:
            acc += v
            seed = acc / period
            out[i] = seed
            continue
        assert seed is not None
        seed = v * k + seed * (1 - k)
        out[i] = seed
    return out


def sma(values: Sequence[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if period <= 0:
        return out
    acc = 0.0
    for i, v in enumerate(values):
        acc += v
        if i >= period:
            acc -= values[i - period]
        if i >= period - 1:
            out[i] = acc / period
    return out


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period + 1:
        return out
    gains = []
    losses = []
    for i in range(1, len(values)):
        d = values[i] - values[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    out[period] = 100.0 if avg_l == 0 else 100 - (100 / (1 + avg_g / avg_l))
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
        out[i + 1] = 100.0 if avg_l == 0 else 100 - (100 / (1 + avg_g / avg_l))
    return out


def macd(
    values: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    ef = ema(values, fast)
    es = ema(values, slow)
    line: list[float | None] = []
    for a, b in zip(ef, es):
        line.append(None if a is None or b is None else a - b)
    # signal on available macd values
    compact = [x for x in line if x is not None]
    sig_compact = ema(compact, signal)
    sig: list[float | None] = [None] * len(line)
    j = 0
    for i, v in enumerate(line):
        if v is None:
            continue
        sig[i] = sig_compact[j]
        j += 1
    hist = [None if a is None or b is None else a - b for a, b in zip(line, sig)]
    return line, sig, hist


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> list[float | None]:
    n = min(len(highs), len(lows), len(closes))
    out: list[float | None] = [None] * n
    if n < 2:
        return out
    trs = []
    for i in range(1, n):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    if len(trs) < period:
        return out
    avg = sum(trs[:period]) / period
    out[period] = avg
    for i in range(period, len(trs)):
        avg = (avg * (period - 1) + trs[i]) / period
        out[i + 1] = avg
    return out


def bollinger(values: Sequence[float], period: int = 20, mult: float = 2.0) -> tuple[list[float | None], list[float | None], list[float | None], list[float | None]]:
    mid = sma(values, period)
    upper: list[float | None] = [None] * len(values)
    lower: list[float | None] = [None] * len(values)
    width: list[float | None] = [None] * len(values)
    for i in range(len(values)):
        if mid[i] is None or i < period - 1:
            continue
        window = values[i - period + 1 : i + 1]
        mean = mid[i]
        var = sum((x - mean) ** 2 for x in window) / period
        sd = math.sqrt(var)
        upper[i] = mean + mult * sd
        lower[i] = mean - mult * sd
        width[i] = (upper[i] - lower[i]) / mean if mean else None
    return mid, upper, lower, width


def adx(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> list[float | None]:
    """Simplified ADX approximation."""
    n = min(len(highs), len(lows), len(closes))
    out: list[float | None] = [None] * n
    if n < period + 2:
        return out
    plus_dm = []
    minus_dm = []
    trs = []
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    # Wilder smooth
    atr_v = sum(trs[:period]) / period
    p_dm = sum(plus_dm[:period]) / period
    m_dm = sum(minus_dm[:period]) / period
    dxes = []
    for i in range(period, len(trs)):
        atr_v = (atr_v * (period - 1) + trs[i]) / period
        p_dm = (p_dm * (period - 1) + plus_dm[i]) / period
        m_dm = (m_dm * (period - 1) + minus_dm[i]) / period
        p_di = 100 * p_dm / atr_v if atr_v else 0
        m_di = 100 * m_dm / atr_v if atr_v else 0
        denom = p_di + m_di
        dx = 100 * abs(p_di - m_di) / denom if denom else 0
        dxes.append(dx)
        if len(dxes) == period:
            out[i + 1] = sum(dxes) / period
        elif len(dxes) > period:
            prev = out[i]
            out[i + 1] = ((prev or dx) * (period - 1) + dx) / period
    return out


def last(series: Sequence[float | None]) -> float | None:
    for v in reversed(series):
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            return float(v)
    return None
