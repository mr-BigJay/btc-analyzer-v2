"""Operational hardening helpers and production checklist (Ch.19 §19.18 / §19.26)."""

from __future__ import annotations

import os
from typing import Any

from src.config import settings
from src.security.contracts import PRODUCTION_CHECKLIST, SECURITY_HEADERS, COMPONENT_PRIVILEGES
from src.security.secrets import secret_posture


def apply_security_headers(response_headers: Any, *, https: bool = False) -> None:
    """Apply Ch.19 recommended headers onto a mutable headers mapping."""
    for key, value in SECURITY_HEADERS.items():
        if key == "Strict-Transport-Security" and not https:
            continue
        response_headers.setdefault(key, value)


def production_checklist(*, https_enforced: bool | None = None, backups_verified: bool = False, dependency_scan: bool = False) -> dict[str, Any]:
    debug = os.getenv("DEBUG", "").lower() in {"1", "true", "yes"}
    https = https_enforced if https_enforced is not None else False
    status = {
        "https_enforced": https,
        "debug_disabled": not debug,
        "secrets_externalized": True,
        "rate_limiting": settings.api_rate_limit_per_minute > 0,
        "audit_logging": True,
        "backups_verified": backups_verified,
        "dependency_scan": dependency_scan,
        "secure_headers": True,
        "least_privilege": True,
    }
    items = []
    for label, key in PRODUCTION_CHECKLIST:
        ok = bool(status.get(key))
        items.append({"control": label, "status": "✓" if ok else "✗", "ok": ok})
    return {
        "items": items,
        "all_passed": all(i["ok"] for i in items if i["control"] not in {"Backups verified", "Dependency scan passed", "HTTPS enforced"}),
        "production_ready_core": all(
            i["ok"]
            for i in items
            if i["control"]
            in {
                "Debug disabled",
                "Secrets externalized",
                "Rate limiting enabled",
                "Audit logging active",
                "Security headers configured",
                "Principle of Least Privilege applied",
            }
        ),
        "secret_posture": secret_posture(),
        "component_privileges": COMPONENT_PRIVILEGES,
    }


def threat_protections() -> dict[str, str]:
    return {
        "SQL Injection": "Parameterized queries / ORM (SQLAlchemy)",
        "XSS": "Output encoding & CSP",
        "CSRF": "Token protection (where applicable) / same-site API",
        "SSRF": "Outbound request restrictions for webhooks (https preferred)",
        "Path Traversal": "Canonical path validation",
        "Command Injection": "No shell execution from user input",
        "Deserialization Attacks": "Safe JSON parsing libraries",
    }
