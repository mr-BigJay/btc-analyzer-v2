"""Market Structure Engine — HH/HL, BOS, ranges (Ch.2 §2.4)."""

from __future__ import annotations

from src.core import AnalysisObject, ChartObject


class MarketStructureEngine:
    ENGINE = "structure"

    def analyze(self, chart: ChartObject) -> AnalysisObject:
        raise NotImplementedError("Awaiting Design Book Chapter 3+")
