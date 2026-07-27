"""Futures analysis adapter — maps Ch.6 FuturesLayer → AnalysisObject."""

from __future__ import annotations

from src.analysis.context import MarketContext, build_market_context
from src.analysis.layers.futures import FuturesLayer
from src.core import AnalysisObject, ChartObject, FlowObject, ModuleResult


class FuturesAnalysisEngine:
    ENGINE = "futures"

    def analyze(self, flow: ModuleResult[FlowObject] | FlowObject | MarketContext | None = None) -> AnalysisObject:
        if isinstance(flow, MarketContext):
            ctx = flow
        else:
            ctx = build_market_context()
            if isinstance(flow, ModuleResult) and flow.data is not None:
                d = flow.data
                ctx.funding_rate = d.funding_rate
                ctx.open_interest = d.open_interest
                ctx.open_interest_value = d.open_interest_value
                ctx.long_short_ratio = d.long_short_ratio
                ctx.mark_price = d.mark_price
                ctx.liquidations = d.liquidations or {}
                ctx.order_book = d.order_book or {}
            elif isinstance(flow, FlowObject):
                ctx.funding_rate = flow.funding_rate
                ctx.open_interest = flow.open_interest
                ctx.mark_price = flow.mark_price
        result = FuturesLayer().analyze(ctx)
        return AnalysisObject(
            engine=self.ENGINE,
            bias=result.signal.lower().replace(" ", "_"),
            confidence=result.confidence / 100.0,
            signals=result.tags,
            details=result.details,
            rationale=result.summary,
        )
