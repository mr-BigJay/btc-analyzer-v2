"""Market read-model service (Ch.5)."""

from __future__ import annotations

from typing import Any

from src.cache.keys import CacheKeys
from src.storage.redis_cache import redis_cache
from src.storage.repository import CentralRepository


class MarketService:
    """Read-model for dashboard/API — Redis first, repository second."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()

    def snapshot(self) -> dict[str, Any]:
        return {
            "mark_price": redis_cache.get(CacheKeys.LATEST_MARK_PRICE),
            "funding_rate": redis_cache.get(CacheKeys.LATEST_FUNDING_RATE),
            "open_interest": redis_cache.get(CacheKeys.CURRENT_OPEN_INTEREST),
            "order_book": redis_cache.get(CacheKeys.CURRENT_ORDER_BOOK),
            "daily_outlook": redis_cache.get(CacheKeys.LATEST_DAILY_OUTLOOK),
            "trading_plan": redis_cache.get(CacheKeys.ACTIVE_TRADING_PLAN),
            "option_chain_summary": redis_cache.get(CacheKeys.LATEST_OPTION_CHAIN_SUMMARY),
            "cache_backend": redis_cache.backend,
        }
