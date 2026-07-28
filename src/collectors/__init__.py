"""Data collectors — Layer 2 Collection & Exchange Integration (Ch.3 / Ch.12).

Independent per-exchange collectors. No collector talks to another.
No downstream component communicates directly with exchange APIs.
"""

from src.collectors.binance import BinanceFuturesCollector
from src.collectors.bitunix import BitunixCollector
from src.collectors.coinex import CoinExCollector
from src.collectors.contract import SCHEMA_VERSION, stamp_contract
from src.collectors.deribit import DeribitOptionsCollector
from src.collectors.engine import CollectionCycleResult, DataCollectionEngine
from src.collectors.events import MarketEvent, event_bus
from src.collectors.health import CollectorHealthStatus, health_monitor
from src.collectors.interface import ExchangeCollector
from src.collectors.metrics import PERFORMANCE_TARGETS, metrics_registry
from src.collectors.quarantine import quarantine_store
from src.collectors.symbols import symbol_registry
from src.collectors.typed import (
    FuturesCollector,
    MacroCollector,
    OptionsCollector,
    SpotCollector,
    VolatilityCollector,
)

__all__ = [
    "CoinExCollector",
    "BinanceFuturesCollector",
    "DeribitOptionsCollector",
    "BitunixCollector",
    "DataCollectionEngine",
    "CollectionCycleResult",
    "ExchangeCollector",
    "event_bus",
    "MarketEvent",
    "health_monitor",
    "CollectorHealthStatus",
    "quarantine_store",
    "symbol_registry",
    "metrics_registry",
    "PERFORMANCE_TARGETS",
    "stamp_contract",
    "SCHEMA_VERSION",
    "SpotCollector",
    "FuturesCollector",
    "OptionsCollector",
    "VolatilityCollector",
    "MacroCollector",
]
