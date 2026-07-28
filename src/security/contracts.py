"""Security framework contracts (Ch.19)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

SECURITY_SCHEMA_VERSION = "1.0"
SECURITY_ENGINE_VERSION = "1.0"


class AuditAction(str, Enum):
    LOGIN = "Login"
    LOGOUT = "Logout"
    AUTH_FAILED = "Failed authentication"
    PERMISSION_DENIED = "Permission denial"
    CONFIG_CHANGE = "Configuration change"
    SECRET_ROTATION = "Secret rotation"
    ADMIN_ACTION = "Administrative action"
    TOKEN_ISSUED = "Token issued"
    TOKEN_REFRESH = "Token refresh"
    WEBHOOK_REGISTERED = "Webhook registered"
    RATE_LIMIT = "Rate limit exceeded"
    LOCKOUT = "Account lockout"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass(frozen=True)
class AuditRecord:
    """Immutable audit trail entry (Ch.19 §19.14)."""

    audit_id: str = field(default_factory=lambda: str(uuid4()))
    action: str = ""
    actor: str = "anonymous"
    role: str = ""
    outcome: str = "success"  # success | failure | denied
    resource: str = ""
    detail: str = ""
    request_id: str = ""
    ip: str = ""
    timestamp: str = field(default_factory=utc_now_iso)
    schema_version: str = SECURITY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SecurityObject:
    """Standard Security Object (Ch.19 §19.25)."""

    authentication: str = "JWT"
    authorization: str = "RBAC"
    transport_security: str = "TLS 1.3"
    rate_limiting: bool = True
    audit_logging: bool = True
    secret_rotation: bool = True
    multi_factor_supported: bool = True
    schema_version: str = SECURITY_SCHEMA_VERSION
    least_privilege: bool = True
    secure_headers: bool = True
    debug_disabled: bool = True
    secrets_externalized: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PRODUCTION_CHECKLIST = [
    ("HTTPS enforced", "https_enforced"),
    ("Debug disabled", "debug_disabled"),
    ("Secrets externalized", "secrets_externalized"),
    ("Rate limiting enabled", "rate_limiting"),
    ("Audit logging active", "audit_logging"),
    ("Backups verified", "backups_verified"),
    ("Dependency scan passed", "dependency_scan"),
    ("Security headers configured", "secure_headers"),
    ("Principle of Least Privilege applied", "least_privilege"),
]

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "X-Frame-Options": "DENY",
}

COMPONENT_PRIVILEGES = {
    "collectors": ["read_market_data", "write_market_tables"],
    "dashboard": ["read_reports", "read_intelligence"],
    "ai_engine": ["read_analysis", "write_ai_decisions"],
    "monitoring": ["read_health", "read_metrics"],
    "reporting": ["read_scores", "write_reports", "write_alerts"],
    "forbidden": {
        "collectors_modify_reports": False,
        "dashboard_access_secrets": False,
        "ai_alter_history": False,
        "monitoring_access_api_credentials": False,
    },
}
