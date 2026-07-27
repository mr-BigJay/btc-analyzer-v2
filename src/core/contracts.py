"""Standardized cross-module contracts (Ch.2 §2.7, §2.10).

Rules:
  - All communication through standardized interfaces
  - No module modifies another module's output
  - Every result includes UTC timestamp + confidence
  - Decision Engine alone may generate trading recommendations
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar


class ModuleStatus(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"  # used cached / partial data
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


T = TypeVar("T")


@dataclass(frozen=True)
class ModuleResult(Generic[T]):
    """Standard envelope returned by every module (Ch.2 §2.7)."""

    module: str
    status: ModuleStatus
    confidence: float
    data: T
    timestamp: str = field(default_factory=utc_now_iso)
    warning: str | None = None
    source_live: bool = True  # False when served from cache (Ch.2 §2.9)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self.data) if hasattr(self.data, "__dataclass_fields__") else self.data
        return {
            "module": self.module,
            "status": self.status.value if isinstance(self.status, ModuleStatus) else self.status,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "data": data,
            "warning": self.warning,
            "source_live": self.source_live,
        }


@dataclass
class NarrativeObject:
    """CoinEx output — daily market narrative."""

    bias: str = "neutral"
    scenarios: list[str] = field(default_factory=list)
    support_levels: list[float] = field(default_factory=list)
    resistance_levels: list[float] = field(default_factory=list)
    summary: str = ""
    raw_ref: str | None = None


@dataclass
class FlowObject:
    """Binance output — market reference / flow (Rule 8: primary futures reference)."""

    symbol: str = "BTCUSDT"
    mark_price: float | None = None
    funding_rate: float | None = None
    open_interest: float | None = None
    long_short_ratio: float | None = None
    premium: float | None = None
    liquidations: dict = field(default_factory=dict)
    order_book: dict = field(default_factory=dict)
    trades_summary: dict = field(default_factory=dict)
    depth_summary: dict = field(default_factory=dict)


@dataclass
class OptionsObject:
    """Deribit output — institutional positioning."""

    currency: str = "BTC"
    put_call_ratio: float | None = None
    implied_volatility: float | None = None
    gamma_exposure: float | None = None
    dealer_position: str = "neutral"
    max_pain: float | None = None
    greeks_summary: dict = field(default_factory=dict)
    option_chain_meta: dict = field(default_factory=dict)


@dataclass
class ChartObject:
    """Technical module output — chart intelligence."""

    symbol: str = "BTCUSDT"
    timeframe: str = "1d"
    trend: str = "neutral"
    support: float | None = None
    resistance: float | None = None
    indicators: dict = field(default_factory=dict)
    patterns: list[str] = field(default_factory=list)
    structure: dict = field(default_factory=dict)


@dataclass
class AnalysisObject:
    """Single analysis-engine verdict (Layer 6). Always explainable + confident."""

    engine: str  # futures | options | technical | pattern | structure
    bias: str = "neutral"
    confidence: float = 0.0
    signals: list[str] = field(default_factory=list)
    levels: dict = field(default_factory=dict)
    rationale: str = ""


@dataclass
class ProbabilityObject:
    """Probability Engine output (Ch.2 §2.6)."""

    bullish_probability: float = 0.5
    bearish_probability: float = 0.5
    confidence: float = 0.0
    preferred_direction: str = "no_trade"
    confirming_engines: list[str] = field(default_factory=list)
    conflicting_engines: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    rationale: str = ""
