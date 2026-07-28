"""API Specification contracts (Ch.18)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

API_SCHEMA_VERSION = "1.0"
API_SPEC_VERSION = "1.0"
COMPATIBILITY_POLICY = {
    "fields_never_repurposed": True,
    "optional_fields_may_be_added": True,
    "deprecated_fields_documented_until_removal": True,
    "breaking_changes_require_major_version": True,
}


class ApiRole(str, Enum):
    VIEWER = "Viewer"
    ANALYST = "Analyst"
    OPERATOR = "Operator"
    ADMINISTRATOR = "Administrator"


ROLE_RANK = {
    ApiRole.VIEWER.value: 1,
    ApiRole.ANALYST.value: 2,
    ApiRole.OPERATOR.value: 3,
    ApiRole.ADMINISTRATOR.value: 4,
}


HTTP_STATUS = {
    200: "Success",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Validation Error",
    429: "Rate Limited",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


RESOURCE_CATEGORIES = [
    "Assets",
    "Spot",
    "Futures",
    "Options",
    "Liquidity",
    "Volatility",
    "Market Intelligence",
    "Reports",
    "Alerts",
    "System",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class Principal:
    """Authenticated caller — independent of business logic."""

    subject: str
    role: str = ApiRole.VIEWER.value
    auth_method: str = "none"  # none | api_key | jwt
    scopes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def has_at_least(self, role: str) -> bool:
        return ROLE_RANK.get(self.role, 0) >= ROLE_RANK.get(role, 99)


@dataclass
class MarketIntelligenceResponse:
    """Canonical external market intelligence interface (Ch.18 §18.25)."""

    asset: str = "BTCUSDT"
    market_bias: str = "Neutral"
    market_regime: str = "Range"
    confidence_score: float = 50.0
    risk_score: float = 40.0
    market_health_index: Any = None
    market_stress_index: Any = None
    primary_scenario: str = ""
    last_updated: str = field(default_factory=utc_now_iso)
    schema_version: str = API_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaginationMeta:
    page: int = 1
    page_size: int = 50
    total_items: int = 0
    total_pages: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WebhookSubscription:
    subscription_id: str = field(default_factory=lambda: str(uuid4()))
    url: str = ""
    events: list[str] = field(default_factory=list)
    secret: str = ""
    active: bool = True
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
