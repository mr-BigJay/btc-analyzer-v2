"""Pattern Engine — chart pattern detection (Ch.2 §2.4).

Pattern detection alone must never trigger a trade (Decision Engine only — Rule 6).
"""

from __future__ import annotations

from src.core import AnalysisObject, ChartObject


class PatternEngine:
    ENGINE = "pattern"

    def analyze(self, chart: ChartObject) -> AnalysisObject:
        raise NotImplementedError("Awaiting Design Book Chapter 3+")
