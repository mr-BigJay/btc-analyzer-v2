"""Technical analysis adapter (Ch.6 TechnicalLayer)."""

from __future__ import annotations

from src.analysis.context import build_market_context
from src.analysis.layers.technical import TechnicalLayer
from src.core import AnalysisObject, ChartObject, ModuleResult


class TechnicalAnalysisEngine:
    ENGINE = "technical"

    def analyze(self, chart: ModuleResult[ChartObject] | ChartObject | None = None) -> AnalysisObject:
        ctx = build_market_context()
        if isinstance(chart, ModuleResult) and chart.data is not None:
            ctx.timeframe = chart.data.timeframe or ctx.timeframe
            if chart.data.ohlcv:
                ctx.ohlcv = chart.data.ohlcv
        elif isinstance(chart, ChartObject):
            ctx.timeframe = chart.timeframe or ctx.timeframe
            if chart.ohlcv:
                ctx.ohlcv = chart.ohlcv
        result = TechnicalLayer().analyze(ctx)
        return AnalysisObject(
            engine=self.ENGINE,
            bias=result.signal.lower().replace(" ", "_"),
            confidence=result.confidence / 100.0,
            signals=result.tags,
            details=result.details,
            rationale=result.summary,
            levels={
                "ema20": result.details.get("ema20"),
                "ema50": result.details.get("ema50"),
            },
        )

    def build_chart(self, symbol: str = "BTCUSDT", timeframe: str = "1d") -> ModuleResult[ChartObject]:
        ctx = build_market_context(symbol=symbol, timeframe=timeframe)
        chart = ChartObject(
            symbol=symbol,
            timeframe=timeframe,
            ohlcv=ctx.ohlcv,
            indicators={},
        )
        from src.core import ModuleStatus

        return ModuleResult(module=self.ENGINE, status=ModuleStatus.OK, confidence=0.8, data=chart)
