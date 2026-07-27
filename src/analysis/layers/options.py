"""Layer 3 — Options Market (Ch.6 §6.4)."""

from __future__ import annotations

from src.analysis.contracts import SignalBias
from src.analysis.context import MarketContext
from src.analysis.layers.base import BaseLayer


class OptionsLayer(BaseLayer):
    NAME = "Options"

    def analyze(self, ctx: MarketContext) -> LayerResult:
        quality = 0.2
        tags: list[str] = []
        details: dict = {}
        score = 0.0

        if ctx.put_call_ratio is not None:
            quality = max(quality, 0.75)
            pcr = ctx.put_call_ratio
            details["put_call_ratio"] = pcr
            if pcr > 1.1:
                tags.append("Bearish Hedging")
                score -= 0.25
            elif pcr < 0.85:
                tags.append("Bullish Hedging")
                score += 0.25

        if ctx.max_pain is not None and ctx.mark_price:
            quality = max(quality, 0.8)
            details["max_pain"] = ctx.max_pain
            dist = (ctx.mark_price - ctx.max_pain) / ctx.max_pain
            details["price_vs_max_pain"] = dist
            if abs(dist) < 0.02:
                tags.append("Gamma Pinning")
            elif dist > 0.03:
                score += 0.1
            elif dist < -0.03:
                score -= 0.1

        if ctx.gamma_exposure is not None:
            quality = max(quality, 0.85)
            details["gamma_exposure"] = ctx.gamma_exposure
            if ctx.gamma_exposure > 0:
                tags.append("Dealer Support")
                score += 0.15
            elif ctx.gamma_exposure < 0:
                tags.append("Dealer Resistance")
                score -= 0.15

        if ctx.volatility_skew is not None:
            details["volatility_skew"] = ctx.volatility_skew
            if ctx.volatility_skew > 0.05:
                tags.append("Bearish Hedging")
                score -= 0.1
            elif ctx.volatility_skew < -0.05:
                tags.append("Bullish Hedging")
                score += 0.1

        if ctx.iv_rank is not None and ctx.iv_rank > 70:
            tags.append("Volatility Expansion")
        elif ctx.implied_volatility_mean is not None:
            details["iv_mean"] = ctx.implied_volatility_mean

        if ctx.option_chain:
            quality = max(quality, 0.9)
            details["chain_size"] = len(ctx.option_chain)

        if quality < 0.4:
            return self._result(
                SignalBias.NEUTRAL.value,
                40,
                "Options data unavailable — neutral.",
                timeframe=ctx.timeframe,
                details=details,
                tags=["Low Data Quality"],
                data_quality=quality,
            )

        signal = self._clamp_signal_from_score(score)
        conf = 50 + abs(score) * 50
        summary = f"Options institutional positioning score={score:.2f}."
        return self._result(
            signal,
            conf,
            summary,
            timeframe=ctx.timeframe,
            details=details,
            tags=list(dict.fromkeys(tags)),
            data_quality=quality,
        )
