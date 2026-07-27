"""Collection service facade (Ch.5)."""

from __future__ import annotations

from typing import Any

from src.cache import redis_cache
from src.collectors.engine import CollectionCycleResult, DataCollectionEngine
from src.storage.repository import CentralRepository


class CollectionService:
    """Facade over collectors — Analysis must not call collectors' internals."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.engine = DataCollectionEngine(repository)

    def run_full(self) -> CollectionCycleResult:
        return self.engine.run_full_cycle_sync()

    def run_minute(self) -> CollectionCycleResult:
        return self.engine.run_minute_cycle_sync()

    def run_technical(self) -> CollectionCycleResult:
        return self.engine.run_technical_cache_sync()

    def run_options(self) -> CollectionCycleResult:
        return self.engine.run_options_cycle_sync()

    def run_narrative(self) -> CollectionCycleResult:
        return self.engine.run_narrative_cycle_sync()

    def status(self) -> dict[str, Any]:
        repo = self.engine.repository
        return {
            "snapshots": {
                "Binance": repo.load_snapshot("Binance") is not None,
                "Deribit": repo.load_snapshot("Deribit") is not None,
                "CoinEx": repo.load_snapshot("CoinEx") is not None,
                "Bitunix": repo.load_snapshot("Bitunix") is not None,
            },
            "hot_cache": redis_cache.snapshot(),
        }
