"""Analysis service facade (Ch.5 / Ch.6)."""

from __future__ import annotations

from typing import Any

from src.analysis.engine import AnalysisEngine
from src.analysis.patterns import PatternEngine
from src.analysis.technical import TechnicalAnalysisEngine
from src.cache.keys import CacheKeys
from src.core import ChartObject
from src.storage.redis_cache import redis_cache
from src.storage.repository import CentralRepository


class AnalysisService:
    """Runs Analysis Engine / layers against repository data — never collectors."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.engine = AnalysisEngine(self.repository)
        self.technical = TechnicalAnalysisEngine()
        self.patterns = PatternEngine()

    def run_full(self, *, timeframe: str = "1h", multi_timeframe: bool = True) -> dict[str, Any]:
        output = self.engine.analyze(timeframe=timeframe, multi_timeframe=multi_timeframe)
        return output.to_dict()

    def refresh_technical(self) -> dict[str, Any]:
        mark = redis_cache.get(CacheKeys.LATEST_MARK_PRICE)
        result = self.technical.analyze(ChartObject(symbol="BTCUSDT", timeframe="1h"))
        return {
            "engine": "technical",
            "status": "OK",
            "bias": result.bias,
            "confidence": result.confidence,
            "signals": result.signals,
            "details": result.details,
            "mark_price": mark,
            "rationale": result.rationale,
        }

    def detect_patterns(self) -> dict[str, Any]:
        result = self.patterns.analyze(ChartObject(symbol="BTCUSDT", timeframe="1h"))
        payload = {
            "engine": "pattern",
            "status": "OK",
            "bias": result.bias,
            "confidence": result.confidence,
            "signals": result.signals,
            "details": result.details,
            "rationale": result.rationale,
        }
        redis_cache.set("latest_pattern_analysis", payload, ttl_sec=900)
        return payload
