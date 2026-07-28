"""Dashboard UX contracts (Ch.17) — presentation only, never mutate analytics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

DASHBOARD_SCHEMA_VERSION = "1.0"
DASHBOARD_ENGINE_VERSION = "1.0"


class DashboardState(str, Enum):
    LOADING = "Loading"
    LIVE = "Live"
    STALE = "Stale"
    DEGRADED = "Degraded"
    OFFLINE = "Offline"
    MAINTENANCE = "Maintenance"


class SemanticColor(str, Enum):
    GREEN = "green"  # Bullish / Positive
    RED = "red"  # Bearish / Negative
    AMBER = "amber"  # Caution
    BLUE = "blue"  # Informational
    GRAY = "gray"  # Neutral / Inactive


class InformationLevel(str, Enum):
    L1_STATUS = "level_1_immediate_status"
    L2_STRATEGY = "level_2_strategic_analysis"
    L3_EVIDENCE = "level_3_detailed_evidence"
    L4_HISTORY = "level_4_historical_context"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class MetricItem:
    label: str
    value: Any = None
    unit: str = ""
    tone: str = SemanticColor.GRAY.value
    hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DomainCard:
    """Consistent intelligence card (Ch.17 §17.8)."""

    id: str
    title: str
    metrics: list[MetricItem] = field(default_factory=list)
    summary: str = ""
    tone: str = SemanticColor.BLUE.value
    icon: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "metrics": [m.to_dict() for m in self.metrics],
            "summary": self.summary,
            "tone": self.tone,
            "icon": self.icon,
        }


@dataclass
class ExplainabilityBlock:
    question: str
    bullets: list[dict[str, Any]] = field(default_factory=list)  # {ok: bool, text: str}
    expandable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Personalization:
    """Presentation preferences only — never affects analytical results."""

    favorite_assets: list[str] = field(default_factory=lambda: ["BTCUSDT"])
    preferred_timeframe: str = "1h"
    layout: str = "default"  # default | compact | focus
    default_report_type: str = "Daily Outlook"
    alert_min_severity: str = "Medium"
    theme: str = "ops-dark"
    display_density: str = "comfortable"  # compact | comfortable | spacious
    reduced_motion: bool = False
    high_contrast: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Personalization":
        raw = dict(data or {})
        allowed = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in raw.items() if k in allowed})


@dataclass
class DashboardView:
    """Canonical dashboard payload for UI rendering (Ch.17)."""

    state: str = DashboardState.LOADING.value
    header: dict[str, Any] = field(default_factory=dict)
    executive: dict[str, Any] = field(default_factory=dict)
    domain_cards: list[dict[str, Any]] = field(default_factory=list)
    narrative: dict[str, Any] = field(default_factory=dict)
    trading_plan: dict[str, Any] = field(default_factory=dict)
    explainability: dict[str, Any] = field(default_factory=dict)
    alerts: dict[str, Any] = field(default_factory=dict)
    historical: dict[str, Any] = field(default_factory=dict)
    navigation: dict[str, Any] = field(default_factory=dict)
    personalization: dict[str, Any] = field(default_factory=dict)
    performance_targets: dict[str, Any] = field(default_factory=dict)
    levels: dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=utc_now_iso)
    schema_version: str = DASHBOARD_SCHEMA_VERSION
    engine_version: str = DASHBOARD_ENGINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
