"""Layer 8 — Liquidity Mapping (Ch.6 §6.4)."""

from __future__ import annotations

from src.analysis.contracts import SignalBias
from src.analysis.context import MarketContext
from src.analysis.layers.base import BaseLayer


class LiquidityLayer(BaseLayer):
    NAME = "Liquidity"

    def analyze(self, ctx: MarketContext) -> LayerResult:
        closes = ctx.closes
        highs = [float(r["high"]) for r in ctx.ohlcv if r.get("high") is not None]
        lows = [float(r["low"]) for r in ctx.ohlcv if r.get("low") is not None]

        if len(closes) < 40:
            return self._result(
                SignalBias.NEUTRAL.value,
                35,
                "Liquidity mapping needs more price history.",
                timeframe=ctx.timeframe,
                data_quality=0.3,
            )

        price = closes[-1]
        tags: list[str] = []
        details: dict = {}
        score = 0.0

        # Equal highs / lows
        eq_highs = _equal_levels(highs[-40:], tol=0.0015)
        eq_lows = _equal_levels(lows[-40:], tol=0.0015)
        details["equal_highs"] = eq_highs
        details["equal_lows"] = eq_lows
        if eq_highs:
            tags.append("Liquidity Above")
            tags.append("Equal Highs")
            tags.append("Stop Clusters")
        if eq_lows:
            tags.append("Liquidity Below")
            tags.append("Equal Lows")
            tags.append("Stop Clusters")

        # Magnet = nearest liquidity pool
        above = [h for h in eq_highs if h > price]
        below = [lo for lo in eq_lows if lo < price]
        if above:
            details["magnet_above"] = min(above)
            tags.append("Magnet Zones")
            # Price often sweeps liquidity then reverses — slight fade toward magnet
            dist = (min(above) - price) / price
            if dist < 0.01:
                tags.append("Sweep Probability")
                score -= 0.1
        if below:
            details["magnet_below"] = max(below)
            tags.append("Magnet Zones")
            dist = (price - max(below)) / price
            if dist < 0.01:
                tags.append("Sweep Probability")
                score += 0.1

        # Fair value gaps (3-candle imbalance)
        fvgs = _fair_value_gaps(highs, lows, closes)
        details["fair_value_gaps"] = fvgs[-5:]
        bull_fvg = [g for g in fvgs if g["type"] == "bullish" and g["low"] <= price <= g["high"]]
        bear_fvg = [g for g in fvgs if g["type"] == "bearish" and g["low"] <= price <= g["high"]]
        if bull_fvg:
            tags.append("Order Blocks")
            score += 0.15
        if bear_fvg:
            tags.append("Order Blocks")
            score -= 0.15

        # Order book walls as liquidity pools
        bids = (ctx.order_book or {}).get("bids") or []
        asks = (ctx.order_book or {}).get("asks") or []
        if bids or asks:
            tags.append("Liquidity Pools")

        signal = self._clamp_signal_from_score(score, bull_thr=0.12, bear_thr=-0.12)
        conf = 50 + abs(score) * 40
        return self._result(
            signal,
            conf,
            f"Liquidity map tags={', '.join(tags) or 'none'}.",
            timeframe=ctx.timeframe,
            details=details,
            tags=list(dict.fromkeys(tags)),
            data_quality=0.8,
        )


def _equal_levels(levels: list[float], tol: float = 0.0015) -> list[float]:
    found = []
    for i, a in enumerate(levels):
        for b in levels[i + 1 :]:
            if abs(a - b) / max(a, b) <= tol:
                mid = (a + b) / 2
                if not any(abs(mid - x) / mid <= tol for x in found):
                    found.append(mid)
    return found


def _fair_value_gaps(highs: list[float], lows: list[float], closes: list[float]) -> list[dict]:
    gaps = []
    n = min(len(highs), len(lows), len(closes))
    for i in range(2, n):
        # bullish FVG: low[i] > high[i-2]
        if lows[i] > highs[i - 2]:
            gaps.append({"type": "bullish", "low": highs[i - 2], "high": lows[i], "index": i})
        # bearish FVG: high[i] < low[i-2]
        if highs[i] < lows[i - 2]:
            gaps.append({"type": "bearish", "low": highs[i], "high": lows[i - 2], "index": i})
    return gaps
