"""Observability contracts (Ch.21)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

OBSERVABILITY_SCHEMA_VERSION = "1.0"
OBSERVABILITY_ENGINE_VERSION = "1.0"


class ServiceStatus(str, Enum):
    HEALTHY = "Healthy"
    DEGRADED = "Degraded"
    UNHEALTHY = "Unhealthy"
    UNKNOWN = "Unknown"


class LogLevel(str, Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class ObservabilityObject:
    """Standard Observability Object (Ch.21 §21.23)."""

    service: str = "api"
    status: str = ServiceStatus.HEALTHY.value
    availability: float = 100.0
    average_latency_ms: float = 0.0
    error_rate: float = 0.0
    active_alerts: int = 0
    data_quality_score: float = 100.0
    last_updated: str = field(default_factory=utc_now_iso)
    schema_version: str = OBSERVABILITY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# SLI definitions (Ch.21 §21.14)
SLIS = {
    "Availability": "Successful request percentage",
    "Latency": "Response time",
    "Data Freshness": "Age of latest market data",
    "Accuracy": "Validation success",
    "Delivery Rate": "Notification success",
}

# SLO targets (Ch.21 §21.15)
SLOS = {
    "api_availability": {"target": 99.9, "unit": "%", "label": "API Availability"},
    "collector_availability": {"target": 99.95, "unit": "%", "label": "Collector Availability"},
    "dashboard_availability": {"target": 99.9, "unit": "%", "label": "Dashboard Availability"},
    "avg_api_latency_ms": {"target": 250.0, "unit": "ms", "label": "Average API Latency", "comparator": "<"},
    "market_data_freshness_sec": {"target": 5.0, "unit": "s", "label": "Market Data Freshness", "comparator": "<"},
}

# Retention (Ch.21 §21.20)
RETENTION = {
    "metrics": "12 months",
    "logs": "90 days",
    "audit_logs": "1 year (or per policy)",
    "traces": "30 days",
    "alerts": "1 year",
}

APPLICATION_METRICS = [
    "Requests per Second",
    "Average Response Time",
    "Error Percentage",
    "Active Sessions",
    "Cache Hit Ratio",
    "Collector Latency",
    "AI Inference Time",
    "Scheduler Execution Time",
]

MARKET_METRICS = [
    "Collector uptime",
    "Data freshness",
    "Missing candles",
    "Exchange latency",
    "API failure rate",
    "WebSocket reconnect frequency",
    "Data Quality Score",
    "Synchronization delay",
]

AI_METRICS = [
    "Average inference time",
    "Confidence distribution",
    "Prediction frequency",
    "Validation accuracy",
    "Prompt version usage",
    "Token consumption",
    "Response consistency",
]

DASHBOARDS = [
    "Executive Health Dashboard",
    "Infrastructure Dashboard",
    "API Performance Dashboard",
    "Collector Dashboard",
    "AI Performance Dashboard",
    "Database Dashboard",
    "Security Dashboard",
    "Alert Analytics Dashboard",
]

ALERT_CONDITIONS = [
    "Service unavailable",
    "API latency exceeds threshold",
    "Database connection failures",
    "Exchange disconnection",
    "High error rate",
    "Data Quality Score degradation",
    "AI response timeout",
    "Excessive memory usage",
]
