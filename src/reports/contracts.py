"""Report Generation contracts (Ch.10 §10.18 / §10.16)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from src import __version__
from src.core.contracts import utc_now_iso

SCHEMA_VERSION = "10.0"
AI_VERSION = "7.0"
SCORING_VERSION = "9.0"
INTELLIGENCE_VERSION = "8.0"


class ReportType(str, Enum):
    DAILY_OUTLOOK = "Daily Outlook"
    INTRADAY_PLAN = "Intraday Trading Plan"
    MARKET_SNAPSHOT = "Market Snapshot"
    FUTURES = "Futures Report"
    OPTIONS = "Options Report"
    LIQUIDITY = "Liquidity Report"
    RISK = "Risk Report"
    WEEKLY = "Weekly Summary"
    ALERT = "Alert Notification"


class Audience(str, Enum):
    EXECUTIVE = "executive"
    PROFESSIONAL = "professional"
    ANALYST = "analyst"


class AlertSeverity(str, Enum):
    INFO = "info"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ReportMetadata:
    report_id: str = field(default_factory=lambda: str(uuid4()))
    generation_time: str = field(default_factory=utc_now_iso)
    analysis_timestamp: str = ""
    engine_version: str = __version__
    ai_version: str = AI_VERSION
    scoring_version: str = SCORING_VERSION
    intelligence_version: str = INTELLIGENCE_VERSION
    data_version: str = ""
    schema_version: str = SCHEMA_VERSION
    symbol: str = "BTCUSDT"
    language: str = "en"
    timezone: str = "UTC"
    audience: str = Audience.PROFESSIONAL.value
    published: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalReport:
    """Canonical report structure (Ch.10 §10.18) — language-independent analytics."""

    report_type: str = ReportType.DAILY_OUTLOOK.value
    generated_at: str = field(default_factory=utc_now_iso)
    market_bias: str = "Neutral"
    confidence: float = 50.0
    market_bias_score: float | None = None
    market_regime: str = "Range"
    market_narrative: str = ""
    executive_summary: str = ""
    key_drivers: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    primary_scenario: dict[str, Any] = field(default_factory=dict)
    alternative_scenarios: list[dict[str, Any]] = field(default_factory=list)
    trading_plan: dict[str, Any] = field(default_factory=dict)
    sections: dict[str, Any] = field(default_factory=dict)
    explainability: dict[str, Any] = field(default_factory=dict)
    confidence_breakdown: list[dict[str, Any]] = field(default_factory=list)
    invalidation_levels: list[float] = field(default_factory=list)
    final_conclusion: str = ""
    disclaimer: str = (
        "Decision Support System output — advisory only. "
        "No guaranteed outcomes. Probabilities are evidence-derived."
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    qa: dict[str, Any] = field(default_factory=dict)
    # Analytical payloads preserved verbatim (presentation must not mutate)
    decision_object: dict[str, Any] = field(default_factory=dict)
    ai_report: dict[str, Any] = field(default_factory=dict)
    market_intelligence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AlertEvent:
    alert_type: str
    severity: str = AlertSeverity.WATCH.value
    message: str = ""
    symbol: str = "BTCUSDT"
    timestamp: str = field(default_factory=utc_now_iso)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
