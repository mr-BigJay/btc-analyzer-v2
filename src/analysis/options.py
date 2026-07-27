"""Options analysis adapter (Ch.6 OptionsLayer)."""

from __future__ import annotations

from src.analysis.context import MarketContext, build_market_context
from src.analysis.layers.options import OptionsLayer
from src.core import AnalysisObject, ModuleResult, OptionsObject


class OptionsAnalysisEngine:
    ENGINE = "options"

    def analyze(self, options: ModuleResult[OptionsObject] | OptionsObject | MarketContext | None = None) -> AnalysisObject:
        if isinstance(options, MarketContext):
            ctx = options
        else:
            ctx = build_market_context()
            data = options.data if isinstance(options, ModuleResult) else options
            if isinstance(data, OptionsObject):
                ctx.put_call_ratio = data.put_call_ratio
                ctx.max_pain = data.max_pain
                ctx.iv_rank = data.iv_rank
                ctx.gamma_exposure = data.gamma_exposure
                ctx.dealer_gamma = data.dealer_gamma
                ctx.volatility_skew = data.volatility_skew
                ctx.option_chain = data.option_chain or []
        result = OptionsLayer().analyze(ctx)
        return AnalysisObject(
            engine=self.ENGINE,
            bias=result.signal.lower().replace(" ", "_"),
            confidence=result.confidence / 100.0,
            signals=result.tags,
            details=result.details,
            rationale=result.summary,
        )
