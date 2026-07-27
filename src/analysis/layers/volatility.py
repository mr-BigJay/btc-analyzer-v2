"""Layer 7 — Volatility (Ch.6 §6.4)."""

from __future__ import annotations

from src.analysis.contracts import SignalBias
from src.analysis.context import MarketContext
from src.analysis.indicators import atr, bollinger, last
from src.analysis.layers.base import BaseLayer


class VolatilityLayer(BaseLayer):
    NAME = "Volatility"

    def analyze(self, ctx: MarketContext) -> LayerResult:
        closes = ctx.closes
        highs = [float(r["high"]) for r in ctx.ohlcv if r.get("high") is not None]
        lows = [float(r["low"]) for r in ctx.ohlcv if r.get("low") is not None]

        if len(closes) < 30:
            return self._result(
                SignalBias.NEUTRAL.value,
                40,
                "Volatility layer awaiting more candles.",
                timeframe=ctx.timeframe,
                data_quality=0.3,
            )

        tags: list[str] = []
        details: dict = {}
        # Historical vol proxy: stdev of returns
        rets = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
        window = rets[-20:]
        mean = sum(window) / len(window)
        var = sum((x - mean) ** 2 for x in window) / len(window)
        hv = (var ** 0.5) * (365 ** 0.5) * 100  # annualized % rough
        details["historical_volatility"] = hv

        _, _, _, width = bollinger(closes, 20)
        w = last(width)
        details["bollinger_width"] = w

        atr_v = None
        if len(highs) == len(closes) and len(lows) == len(closes):
            atr_v = last(atr(highs, lows, closes, 14))
            details["atr"] = atr_v

        if ctx.iv_rank is not None:
            details["iv_rank"] = ctx.iv_rank
            if ctx.iv_rank >= 70:
                tags.append("High Volatility")
                tags.append("Expansion")
            elif ctx.iv_rank <= 30:
                tags.append("Low Volatility")
                tags.append("Compression")

        # BB width regime
        widths = [x for x in width if x is not None]
        if widths and w is not None:
            avg_w = sum(widths[-50:]) / min(50, len(widths))
            if w < avg_w * 0.7:
                tags.append("Compression")
                tags.append("Low Volatility")
            elif w > avg_w * 1.3:
                tags.append("Expansion")
                tags.append("High Volatility")

        # Volatility layer is mostly regime — signal stays Neutral unless extreme
        signal = SignalBias.NEUTRAL.value
        if "Expansion" in tags and "Compression" not in tags:
            conf = 70
        elif "Compression" in tags:
            conf = 68
        else:
            conf = 55
            tags.append("Medium Volatility" if "High Volatility" not in tags else "High Volatility")

        return self._result(
            signal,
            conf,
            f"Volatility regime tags={', '.join(tags)}; HV≈{hv:.1f}.",
            timeframe=ctx.timeframe,
            details=details,
            tags=list(dict.fromkeys(tags)),
            data_quality=0.85,
        )
