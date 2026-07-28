"""Collection service facade (Ch.5 / Ch.12)."""

from __future__ import annotations

from typing import Any

from src.cache import redis_cache
from src.collectors.backfill import HistoricalBackfill
from src.collectors.engine import CollectionCycleResult, DataCollectionEngine
from src.collectors.events import event_bus
from src.collectors.health import health_monitor
from src.collectors.metrics import metrics_registry
from src.collectors.quarantine import quarantine_store
from src.collectors.symbols import symbol_registry
from src.collectors.typed import COLLECTOR_TYPES
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

    def run_typed(self, collector_type: str) -> dict[str, Any]:
        key = collector_type.lower().strip()
        cls = COLLECTOR_TYPES.get(key)
        if cls is None:
            raise ValueError(f"Unknown collector type '{collector_type}'")
        return cls(self.engine.repository).collect().to_dict()

    def backfill(self, *, timeframe: str = "1h", limit: int = 500) -> dict[str, Any]:
        return HistoricalBackfill(self.engine.repository).backfill_ohlcv(timeframe=timeframe, limit=limit).to_dict()

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
            "health": health_monitor.snapshot(),
            "metrics": metrics_registry.snapshot(),
            "quarantine_count": quarantine_store.count(),
            "recent_events": event_bus.recent(limit=10),
            "symbol_registry": symbol_registry.list_mappings()[:12],
            "collector_types": list(COLLECTOR_TYPES.keys()),
        }
