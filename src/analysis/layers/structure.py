"""Layer 5 — Market Structure (Ch.6 §6.4)."""

from __future__ import annotations

from src.analysis.contracts import SignalBias
from src.analysis.context import MarketContext
from src.analysis.layers.base import BaseLayer


class StructureLayer(BaseLayer):
    NAME = "Market Structure"

    def analyze(self, ctx: MarketContext) -> LayerResult:
        closes = ctx.closes
        highs = [float(r["high"]) for r in ctx.ohlcv if r.get("high") is not None]
        lows = [float(r["low"]) for r in ctx.ohlcv if r.get("low") is not None]

        if len(closes) < 40 or len(highs) < 40 or len(lows) < 40:
            return self._result(
                SignalBias.NEUTRAL.value,
                35,
                "Insufficient data for structure detection.",
                timeframe=ctx.timeframe,
                data_quality=0.3,
                tags=["Low Data Quality"],
            )

        swings_h = _swing_highs(highs, left=3, right=3)
        swings_l = _swing_lows(lows, left=3, right=3)
        details = {"swing_highs": swings_h[-4:], "swing_lows": swings_l[-4:]}
        tags: list[str] = []
        score = 0.0

        hh = hl = lh = ll = False
        if len(swings_h) >= 2 and swings_h[-1] > swings_h[-2]:
            hh = True
            tags.append("HH")
        elif len(swings_h) >= 2 and swings_h[-1] < swings_h[-2]:
            lh = True
            tags.append("LH")
        if len(swings_l) >= 2 and swings_l[-1] > swings_l[-2]:
            hl = True
            tags.append("HL")
        elif len(swings_l) >= 2 and swings_l[-1] < swings_l[-2]:
            ll = True
            tags.append("LL")

        details.update({"hh": hh, "hl": hl, "lh": lh, "ll": ll})

        bos = choch = False
        if hh and hl:
            tags.append("Bullish Structure")
            tags.append("Trend Continuation")
            score += 0.55
            # BOS: close above last swing high
            if closes[-1] > swings_h[-1]:
                bos = True
                tags.append("BOS")
                score += 0.15
        elif lh and ll:
            tags.append("Bearish Structure")
            tags.append("Trend Continuation")
            score -= 0.55
            if closes[-1] < swings_l[-1]:
                bos = True
                tags.append("BOS")
                score -= 0.15
        else:
            # Mixed → possible CHoCH
            if (hh and ll) or (lh and hl):
                choch = True
                tags.append("CHoCH")
                tags.append("Structural Reversal")
                score *= 0.3

        details["bos"] = bos
        details["choch"] = choch

        signal = self._clamp_signal_from_score(score)
        conf = 55 + abs(score) * 40
        return self._result(
            signal,
            conf,
            f"Structure tags={', '.join(tags)}; score={score:.2f}.",
            timeframe=ctx.timeframe,
            details=details,
            tags=list(dict.fromkeys(tags)),
            data_quality=0.85,
        )


def _swing_highs(highs: list[float], left: int = 3, right: int = 3) -> list[float]:
    out = []
    for i in range(left, len(highs) - right):
        window = highs[i - left : i + right + 1]
        if highs[i] == max(window):
            out.append(highs[i])
    return out


def _swing_lows(lows: list[float], left: int = 3, right: int = 3) -> list[float]:
    out = []
    for i in range(left, len(lows) - right):
        window = lows[i - left : i + right + 1]
        if lows[i] == min(window):
            out.append(lows[i])
    return out
