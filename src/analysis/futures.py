"""Futures Analysis Engine — interprets Binance FlowObject (Ch.2 §2.4 Layer 6)."""

from __future__ import annotations

from src.core import AnalysisObject, FlowObject, ModuleResult


class FuturesAnalysisEngine:
    ENGINE = "futures"

    def analyze(self, flow: ModuleResult[FlowObject] | FlowObject) -> AnalysisObject:
        raise NotImplementedError("Awaiting Design Book Chapter 3+")
