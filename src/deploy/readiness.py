"""Production readiness and rollback policy (Ch.20 §20.11 / §20.26)."""

from __future__ import annotations

from typing import Any

from src.deploy.contracts import PRODUCTION_READINESS, RPO_MINUTES, RTO_MINUTES
from src.deploy.environments import validate_environment_variables
from src.deploy.probes import health_detailed


def production_readiness(
    *,
    tests_passed: bool = True,
    security_scan: bool = False,
    migrations_validated: bool = True,
    backup_verified: bool = False,
    monitoring: bool = True,
) -> dict[str, Any]:
    env = validate_environment_variables()
    health = health_detailed()
    status = {
        "tests_passed": tests_passed,
        "security_scan": security_scan,
        "migrations_validated": migrations_validated,
        "health_checks": bool(health.get("ok")),
        "backup_verified": backup_verified,
        "rollback_plan": True,
        "monitoring": monitoring,
        "logging": True,
        "env_validated": bool(env.get("ok")),
    }
    items = []
    for label, key in PRODUCTION_READINESS:
        ok = bool(status.get(key))
        items.append({"item": label, "status": "✓" if ok else "✗", "ok": ok})
    # Core gates that must pass before production
    core_keys = {
        "tests_passed",
        "migrations_validated",
        "health_checks",
        "rollback_plan",
        "logging",
        "env_validated",
    }
    core_ok = all(status[k] for k in core_keys)
    return {
        "items": items,
        "core_ok": core_ok,
        "all_passed": all(i["ok"] for i in items),
        "can_deploy_production": core_ok and status["tests_passed"],
        "environment_validation": env,
        "health": health,
    }


def rollback_policy() -> dict[str, Any]:
    return {
        "enabled": True,
        "automated_when_feasible": True,
        "triggers": [
            "Health check failure",
            "Elevated error rate",
            "Performance degradation",
            "Database migration issues",
            "Critical security concerns",
        ],
        "strategies": ["Rolling Update", "Blue-Green"],
        "canary": "Future",
        "rto_minutes": RTO_MINUTES,
        "rpo_minutes": RPO_MINUTES,
    }
