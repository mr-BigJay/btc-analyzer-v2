"""Shared contracts for all modules (Design Book Ch.2 §2.7)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar


class ModuleStatus(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


T = TypeVar("T")


@dataclass
class ModuleResult(Generic[T]):
    """Standard response envelope for every collector/analyzer."""

    module: str
    status: ModuleStatus
    confidence: float
    data: T | None = None
    timestamp: str = field(default_factory=utc_now_iso)
    warning: str | None = None
    source_live: bool = True
    error_code: str | None = None
    retry_count: int = 0
    response_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data: Any = self.data
        if data is not None and hasattr(data, "__dataclass_fields__"):
            data = asdict(data)
        return {
            "module": self.module,
            "status": self.status.value if isinstance(self.status, ModuleStatus) else str(self.status),
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "data": data,
            "warning": self.warning,
            "source_live": self.source_live,
            "error_code": self.error_code,
            "retry_count": self.retry_count,
            "response_time_ms": self.response_time_ms,
        }


@dataclass
class NarrativeObject:
    """CoinEx daily narrative analysis (Ch.2 §2.5 / §2.6)."""

    bias: str = "neutral"
    scenarios: list[str] = field(default_factory=list)
    support_levels: list[float] = field(default_factory=list)
    resistance_levels: list[float] = field(default_factory=list)
    summary: str = ""
    bullish_arguments: list[str] = field(default_factory=list)
    bearish_arguments: list[str] = field(default_factory=list)
    raw_article: str | None = None


@dataclass
class FlowObject:
    """Binance futures market-reference flow (Ch.2 §2.5 / §2.6)."""

    symbol: str = "BTCUSDT"
    mark_price: float | None = None
    index_price: float | None = None
    funding_rate: float | None = None
    funding_history: list[dict] = field(default_factory=list)
    open_interest: float | None = None
    open_interest_value: float | None = None
    long_short_ratio: float | None = None
    premium_index: float | None = None
    basis: float | None = None
    liquidations: dict = field(default_factory=dict)
    order_book: dict = field(default_factory=dict)
    volume: float | None = None


@dataclass
class OptionsObject:
    """Deribit options intelligence (Ch.2 §2.5 / §2.6)."""

    currency: str = "BTC"
    put_call_ratio: float | None = None
    max_pain: float | None = None
    iv_rank: float | None = None
    iv_percentile: float | None = None
    gamma_exposure: float | None = None
    dealer_gamma: float | None = None
    dealer_delta: float | None = None
    volatility_skew: float | None = None
    option_chain: list[dict] = field(default_factory=list)
    volume: float | None = None
    open_interest: float | None = None


@dataclass
class ChartObject:
    """Technical / chart intelligence object (Ch.2 §2.5 / §2.6)."""

    symbol: str = "BTCUSDT"
    timeframe: str = "1d"
    trend: str = "neutral"
    support: float | None = None
    resistance: float | None = None
    indicators: dict = field(default_factory=dict)
    patterns: list[str] = field(default_factory=list)
    structure: dict = field(default_factory=dict)
    ohlcv: list[dict] = field(default_factory=list)


@dataclass
class AnalysisObject:
    """Per-engine analysis verdict (Layer 6)."""

    engine: str
    bias: str = "neutral"
    confidence: float = 0.0
    signals: list[str] = field(default_factory=list)
    levels: dict = field(default_factory=dict)
    details: dict = field(default_factory=dict)
    rationale: str = ""


@dataclass
class ProbabilityObject:
    """Merged probability assessment from the AI layer."""

    bullish_probability: float = 0.5
    bearish_probability: float = 0.5
    confidence: float = 0.0
    preferred_direction: str = "no_trade"
    confirming_layers: list[str] = field(default_factory=list)
    conflicting_layers: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    rationale: str = ""
    scenarios: list[dict] = field(default_factory=list)
