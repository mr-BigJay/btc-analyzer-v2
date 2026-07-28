"""Alerting & Event Processing contracts (Ch.16)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

EVENT_SCHEMA_VERSION = "1.0"
EVENT_ENGINE_VERSION = "1.0"
RULES_VERSION = "1.0"


class EventCategory(str, Enum):
    PRICE = "Price"
    TREND = "Trend"
    FUTURES = "Futures"
    OPTIONS = "Options"
    LIQUIDITY = "Liquidity"
    RISK = "Risk"
    SYSTEM = "System"
    MACRO = "Macro"


class EventSeverity(str, Enum):
    INFORMATIONAL = "Informational"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class EventState(str, Enum):
    DETECTED = "Detected"
    CONFIRMED = "Confirmed"
    ACTIVE = "Active"
    UPDATED = "Updated"
    RESOLVED = "Resolved"
    ARCHIVED = "Archived"


class DeliveryStatus(str, Enum):
    QUEUED = "Queued"
    SENT = "Sent"
    DELIVERED = "Delivered"
    FAILED = "Failed"
    RETRIED = "Retried"
    SUPPRESSED = "Suppressed"


class NotificationChannel(str, Enum):
    API = "API"
    DASHBOARD = "Dashboard"
    TELEGRAM = "Telegram"
    WEBSOCKET = "WebSocket"


SEVERITY_RANK = {
    EventSeverity.INFORMATIONAL.value: 0,
    EventSeverity.LOW.value: 1,
    EventSeverity.MEDIUM.value: 2,
    EventSeverity.HIGH.value: 3,
    EventSeverity.CRITICAL.value: 4,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def new_event_id() -> str:
    return str(uuid4())


@dataclass
class DeliveryRecord:
    channel: str
    status: str = DeliveryStatus.QUEUED.value
    attempts: int = 0
    last_error: str = ""
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EventObject:
    """Standard Event Object (Ch.16 §16.19) — canonical system event."""

    event_id: str = field(default_factory=new_event_id)
    asset: str = "BTCUSDT"
    category: str = EventCategory.TREND.value
    type: str = ""
    severity: str = EventSeverity.MEDIUM.value
    state: str = EventState.DETECTED.value
    timestamp: str = field(default_factory=utc_now_iso)
    summary: str = ""
    explanation: str = ""
    related_events: list[str] = field(default_factory=list)
    notification_channels: list[str] = field(default_factory=list)
    trigger_conditions: dict[str, Any] = field(default_factory=dict)
    related_metrics: dict[str, Any] = field(default_factory=dict)
    notification_history: list[dict[str, Any]] = field(default_factory=list)
    fingerprint: str = ""
    correlated: bool = False
    correlation_label: str = ""
    duplicate_of: str | None = None
    suppressed: bool = False
    suppression_reason: str = ""
    escalated_from: str | None = None
    resolved_at: str | None = None
    rules_version: str = RULES_VERSION
    schema_version: str = EVENT_SCHEMA_VERSION
    engine_version: str = EVENT_ENGINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EventObject":
        raw = dict(data or {})
        allowed = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in raw.items() if k in allowed})

    def transition(self, new_state: str) -> None:
        """Immutable transition log via notification_history; state updated."""
        prev = self.state
        self.state = new_state
        self.notification_history.append(
            {
                "kind": "state_transition",
                "from": prev,
                "to": new_state,
                "at": utc_now_iso(),
            }
        )
