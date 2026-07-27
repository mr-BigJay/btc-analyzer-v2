"""Analysis service facade (Ch.5)."""

from __future__ import annotations

from typing import Any

from src.analysis.patterns import PatternEngine
from src.analysis.technical import TechnicalAnalysisEngine
from src.cache.keys import CacheKeys
from src.core import ChartObject, ModuleStatus
from src.storage.redis_cache import redis_cache
from src.storage.repository import CentralRepository


class AnalysisService:
    """Runs analysis engines against repository/cache data — never collectors directly."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.technical = TechnicalAnalysisEngine()
        self.patterns = PatternEngine()

    def refresh_technical(self) -> dict[str, Any]:
        mark = redis_cache.get(CacheKeys.LATEST_MARK_PRICE)
        chart = ChartObject(symbol="BTCUSDT", timeframe="1h")
        try:
            result = self.technical.analyze(chart)
            return {
                "engine": "technical",
                "status": "OK",
                "bias": result.bias,
                "confidence": result.confidence,
                "signals": result.signals,
                "mark_price": mark,
            }
        except NotImplementedError:
            return {
                "engine": "technical",
                "status": ModuleStatus.SKIPPED.value,
                "mark_price": mark,
                "warning": "TechnicalEngine awaiting Design Book Chapter 6+",
            }

    def detect_patterns(self) -> dict[str, Any]:
        chart = ChartObject(symbol="BTCUSDT", timeframe="1h")
        try:
            result = self.patterns.analyze(chart)
            payload = {
                "engine": "pattern",
                "status": "OK",
                "bias": result.bias,
                "confidence": result.confidence,
                "signals": result.signals,
            }
            redis_cache.set("latest_pattern_analysis", payload, ttl_sec=900)
            return payload
        except NotImplementedError:
            payload = {
                "engine": "pattern",
                "status": ModuleStatus.SKIPPED.value,
                "warning": "PatternEngine awaiting Design Book Chapter 6+",
            }
            redis_cache.set("latest_pattern_analysis", payload, ttl_sec=900)
            return payload
