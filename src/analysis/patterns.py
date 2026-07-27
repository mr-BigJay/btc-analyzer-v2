"""Pattern engine adapter (Ch.6 PatternLayer)."""

from __future__ import annotations

from src.analysis.context import build_market_context
from src.analysis.layers.patterns import PatternLayer
from src.core import AnalysisObject, ChartObject


class PatternEngine:
    ENGINE = "pattern"

    def analyze(self, chart: ChartObject | None = None) -> AnalysisObject:
        ctx = build_market_context(timeframe=(chart.timeframe if chart else "1h"))
        if chart and chart.ohlcv:
            ctx.ohlcv = chart.ohlcv
        result = PatternLayer().analyze(ctx)
        return AnalysisObject(
            engine=self.ENGINE,
            bias=result.signal.lower().replace(" ", "_"),
            confidence=result.confidence / 100.0,
            signals=result.tags,
            details=result.details,
            rationale=result.summary,
            levels={"breakout_target": result.details.get("breakout_target")},
        )
