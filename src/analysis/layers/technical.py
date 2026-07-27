"""Layer 4 — Technical Analysis (Ch.6 §6.4)."""

from __future__ import annotations

from src.analysis.contracts import SignalBias
from src.analysis.context import MarketContext
from src.analysis.indicators import adx, atr, bollinger, ema, last, macd, rsi
from src.analysis.layers.base import BaseLayer


class TechnicalLayer(BaseLayer):
    NAME = "Technical"

    def analyze(self, ctx: MarketContext) -> LayerResult:
        closes = ctx.closes
        highs = [_f(r.get("high")) for r in ctx.ohlcv]
        lows = [_f(r.get("low")) for r in ctx.ohlcv]
        highs_f = [h for h in highs if h is not None]
        lows_f = [lo for lo in lows if lo is not None]

        if len(closes) < 30:
            return self._result(
                SignalBias.NEUTRAL.value,
                35,
                "Not enough OHLCV for technical analysis.",
                timeframe=ctx.timeframe,
                data_quality=0.3,
                tags=["Low Data Quality"],
            )

        quality = min(1.0, len(closes) / 100)
        tags: list[str] = []
        details: dict = {}
        score = 0.0

        e20 = last(ema(closes, 20))
        e50 = last(ema(closes, 50))
        e100 = last(ema(closes, 100)) if len(closes) >= 100 else None
        e200 = last(ema(closes, 200)) if len(closes) >= 200 else None
        details.update({"ema20": e20, "ema50": e50, "ema100": e100, "ema200": e200})

        price = closes[-1]
        if e20 and e50:
            if e20 > e50 and price > e20:
                tags.append("Trend Strength")
                score += 0.35
            elif e20 < e50 and price < e20:
                tags.append("Trend Strength")
                score -= 0.35

        r = last(rsi(closes, 14))
        details["rsi"] = r
        if r is not None:
            if r >= 70:
                tags.append("Overbought")
                score -= 0.15
            elif r <= 30:
                tags.append("Oversold")
                score += 0.15
            elif r >= 55:
                tags.append("Momentum")
                score += 0.1
            elif r <= 45:
                tags.append("Momentum")
                score -= 0.1

        macd_line, macd_sig, hist = macd(closes)
        h = last(hist)
        details["macd_hist"] = h
        if h is not None:
            score += max(-0.25, min(0.25, h / (abs(price) * 0.001 + 1e-9)))

        if len(highs_f) == len(closes) and len(lows_f) == len(closes):
            adx_v = last(adx(highs_f, lows_f, closes, 14))
            atr_v = last(atr(highs_f, lows_f, closes, 14))
            details["adx"] = adx_v
            details["atr"] = atr_v
            if adx_v and adx_v > 25:
                tags.append("Trend Strength")
                score *= 1.1

        _, upper, lower, width = bollinger(closes, 20)
        u, lo, w = last(upper), last(lower), last(width)
        details["bb_width"] = w
        if u and lo and price >= u:
            tags.append("Breakout Probability")
            score += 0.1
        elif u and lo and price <= lo:
            tags.append("Breakout Probability")
            score -= 0.1

        signal = self._clamp_signal_from_score(score)
        conf = 50 + abs(score) * 45
        return self._result(
            signal,
            conf,
            f"Technical score={score:.2f}; RSI={r}; trend tags={tags}.",
            timeframe=ctx.timeframe,
            details=details,
            tags=list(dict.fromkeys(tags)),
            data_quality=quality,
        )


def _f(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
