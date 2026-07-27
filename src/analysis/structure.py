"""Market structure adapter (Ch.6 StructureLayer)."""

from __future__ import annotations

from src.analysis.context import build_market_context
from src.analysis.layers.structure import StructureLayer
from src.core import AnalysisObject, ChartObject


class MarketStructureEngine:
    ENGINE = "structure"

    def analyze(self, chart: ChartObject | None = None) -> AnalysisObject:
        ctx = build_market_context(timeframe=(chart.timeframe if chart else "1h"))
        if chart and chart.ohlcv:
            ctx.ohlcv = chart.ohlcv
        result = StructureLayer().analyze(ctx)
        return AnalysisObject(
            engine=self.ENGINE,
            bias=result.signal.lower().replace(" ", "_"),
            confidence=result.confidence / 100.0,
            signals=result.tags,
            details=result.details,
            rationale=result.summary,
            levels={
                "hh": result.details.get("hh"),
                "hl": result.details.get("hl"),
                "lh": result.details.get("lh"),
                "ll": result.details.get("ll"),
            },
        )
