"""Layer 2 — Futures Market (Ch.6 §6.4)."""

from __future__ import annotations

from src.analysis.contracts import SignalBias
from src.analysis.context import MarketContext
from src.analysis.layers.base import BaseLayer


class FuturesLayer(BaseLayer):
    NAME = "Futures"

    def analyze(self, ctx: MarketContext) -> LayerResult:
        quality = 0.2
        tags: list[str] = []
        details: dict = {}
        score = 0.0

        fr = ctx.funding_rate
        oi = ctx.open_interest
        ls = ctx.long_short_ratio

        if fr is not None:
            quality = max(quality, 0.7)
            details["funding_rate"] = fr
            # Mild positive funding = leveraged longs; extreme = overcrowded
            if fr > 0.0005:
                tags.append("Leveraged Bullish")
                score += 0.25
            elif fr < -0.0005:
                tags.append("Leveraged Bearish")
                score -= 0.25
            if abs(fr) > 0.0015:
                tags.append("Overcrowded Market")
                # Extreme funding fades
                score *= 0.5
                if fr > 0:
                    tags.append("Long Squeeze Risk")
                    score -= 0.2
                else:
                    tags.append("Short Squeeze Risk")
                    score += 0.2

        if oi is not None:
            quality = max(quality, 0.75)
            details["open_interest"] = oi
            details["open_interest_value"] = ctx.open_interest_value
            # Rising OI alone is ambiguous; combine with funding
            if fr is not None and fr > 0 and oi > 0:
                tags.append("Leveraged Bullish")
                score += 0.15
            elif fr is not None and fr < 0 and oi > 0:
                tags.append("Leveraged Bearish")
                score -= 0.15

        if ls is not None:
            quality = max(quality, 0.8)
            details["long_short_ratio"] = ls
            if ls > 1.3:
                tags.append("Overcrowded Market")
                tags.append("Long Squeeze Risk")
                score -= 0.2
            elif ls < 0.75:
                tags.append("Short Squeeze Risk")
                score += 0.2

        liq = ctx.liquidations or {}
        if liq:
            details["liquidations"] = liq
            quality = max(quality, 0.7)

        if quality < 0.4:
            return self._result(
                SignalBias.NEUTRAL.value,
                40,
                "Futures metrics incomplete — neutral.",
                timeframe=ctx.timeframe,
                details=details,
                tags=["Low Data Quality"],
                data_quality=quality,
            )

        signal = self._clamp_signal_from_score(score)
        conf = 50 + abs(score) * 50
        # Build summary like the design example
        parts = []
        if oi is not None and fr is not None:
            oi_dir = "increasing" if oi else "present"
            fr_dir = "positive" if fr > 0 else "negative" if fr < 0 else "flat"
            parts.append(f"Open Interest {oi_dir} alongside {fr_dir} Funding.")
        summary = " ".join(parts) if parts else f"Futures score={score:.2f}."
        return self._result(
            signal,
            conf,
            summary,
            timeframe=ctx.timeframe,
            details=details,
            tags=list(dict.fromkeys(tags)),
            data_quality=quality,
        )
