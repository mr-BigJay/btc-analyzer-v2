"""Layer 6 — Pattern Detection (Ch.6 §6.4)."""

from __future__ import annotations

from src.analysis.contracts import SignalBias
from src.analysis.context import MarketContext
from src.analysis.layers.base import BaseLayer


class PatternLayer(BaseLayer):
    NAME = "Pattern Detection"

    def analyze(self, ctx: MarketContext) -> LayerResult:
        closes = ctx.closes
        highs = [float(r["high"]) for r in ctx.ohlcv if r.get("high") is not None]
        lows = [float(r["low"]) for r in ctx.ohlcv if r.get("low") is not None]

        if len(closes) < 50:
            return self._result(
                SignalBias.NEUTRAL.value,
                30,
                "Insufficient candles for pattern detection.",
                timeframe=ctx.timeframe,
                data_quality=0.3,
                tags=["Low Data Quality"],
            )

        patterns: list[dict] = []
        # Double top / bottom (simplified)
        if len(highs) >= 30:
            h1, h2 = max(highs[-30:-10]), max(highs[-10:])
            if abs(h1 - h2) / max(h1, h2) < 0.004 and closes[-1] < min(highs[-15:]):
                patterns.append(
                    {
                        "name": "Double Top",
                        "direction": "Bearish",
                        "confidence": 62,
                        "target": closes[-1] - (h2 - min(lows[-20:])),
                    }
                )
        if len(lows) >= 30:
            l1, l2 = min(lows[-30:-10]), min(lows[-10:])
            if abs(l1 - l2) / max(abs(l1), abs(l2), 1) < 0.004 and closes[-1] > max(lows[-15:]):
                patterns.append(
                    {
                        "name": "Double Bottom",
                        "direction": "Bullish",
                        "confidence": 62,
                        "target": closes[-1] + (max(highs[-20:]) - l2),
                    }
                )

        # Triangle / compression via range contraction
        recent_range = max(highs[-20:]) - min(lows[-20:])
        prior_range = max(highs[-40:-20]) - min(lows[-40:-20])
        if prior_range > 0 and recent_range / prior_range < 0.55:
            patterns.append(
                {
                    "name": "Triangle",
                    "direction": "Neutral",
                    "confidence": 58,
                    "target": closes[-1],
                }
            )

        # Flag: sharp move then consolidation
        move = closes[-25] - closes[-40] if len(closes) >= 40 else 0
        cons = max(highs[-12:]) - min(lows[-12:])
        if abs(move) / closes[-1] > 0.03 and cons / closes[-1] < 0.012:
            patterns.append(
                {
                    "name": "Flag",
                    "direction": "Bullish" if move > 0 else "Bearish",
                    "confidence": 60,
                    "target": closes[-1] + move * 0.5,
                }
            )

        # Channel
        if len(closes) >= 40:
            slope = (closes[-1] - closes[-40]) / 40
            if abs(slope) / closes[-1] < 0.0005:
                patterns.append({"name": "Rectangle", "direction": "Neutral", "confidence": 55, "target": closes[-1]})
            elif abs(slope) / closes[-1] > 0.0008:
                patterns.append(
                    {
                        "name": "Channel",
                        "direction": "Bullish" if slope > 0 else "Bearish",
                        "confidence": 57,
                        "target": closes[-1] + slope * 10,
                    }
                )

        if not patterns:
            return self._result(
                SignalBias.NEUTRAL.value,
                45,
                "No high-confidence classical patterns detected.",
                timeframe=ctx.timeframe,
                details={"patterns": []},
                data_quality=0.7,
            )

        best = max(patterns, key=lambda p: p["confidence"])
        direction = best["direction"]
        if direction == "Bullish":
            signal = SignalBias.BULLISH.value
        elif direction == "Bearish":
            signal = SignalBias.BEARISH.value
        else:
            signal = SignalBias.NEUTRAL.value

        return self._result(
            signal,
            float(best["confidence"]),
            f"Pattern={best['name']} direction={direction}.",
            timeframe=ctx.timeframe,
            details={"patterns": patterns, "breakout_target": best.get("target")},
            tags=[best["name"], direction],
            data_quality=0.8,
        )
