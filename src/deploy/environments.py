"""Environment detection and configuration validation (Ch.20 §20.4 / §20.7)."""

from __future__ import annotations

import os
from typing import Any

from src.config import settings
from src.deploy.contracts import REQUIRED_ENV_KEYS, Environment


def resolve_environment(explicit: str | None = None) -> str:
    raw = (explicit or os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "development").strip().lower()
    mapping = {
        "dev": Environment.DEVELOPMENT.value,
        "development": Environment.DEVELOPMENT.value,
        "test": Environment.TESTING.value,
        "testing": Environment.TESTING.value,
        "stage": Environment.STAGING.value,
        "staging": Environment.STAGING.value,
        "prod": Environment.PRODUCTION.value,
        "production": Environment.PRODUCTION.value,
    }
    return mapping.get(raw, Environment.DEVELOPMENT.value)


def validate_environment_variables(*, require_redis: bool = False, require_jwt_override: bool = False) -> dict[str, Any]:
    missing = []
    warnings = []
    present = {}
    for key in REQUIRED_ENV_KEYS:
        val = os.getenv(key)
        if key == "DATABASE_URL":
            val = val or settings.database_url
        if key == "REDIS_URL":
            val = val or settings.redis_url or ""
        if key == "API_JWT_SECRET":
            val = val or os.getenv("JWT_SECRET") or settings.api_jwt_secret
        if key == "LOG_LEVEL":
            val = val or settings.log_level
        if key == "TIMEZONE":
            val = val or settings.timezone
        if key == "APP_ENV":
            val = val or os.getenv("ENVIRONMENT") or "development"
        present[key] = bool(val)
        if not val and key in {"DATABASE_URL", "LOG_LEVEL", "TIMEZONE", "APP_ENV"}:
            missing.append(key)
        if key == "REDIS_URL" and require_redis and not val:
            missing.append(key)
        if key == "API_JWT_SECRET" and require_jwt_override and val == "btc-analyzer-dev-secret-change-me":
            warnings.append("API_JWT_SECRET / JWT_SECRET is still the development default")
        if key == "API_JWT_SECRET" and not val:
            missing.append(key)

    env = resolve_environment()
    if env == Environment.PRODUCTION.value:
        if settings.api_jwt_secret == "btc-analyzer-dev-secret-change-me":
            warnings.append("Production must override API_JWT_SECRET")
        if not (settings.redis_url or os.getenv("REDIS_URL")):
            warnings.append("Production should configure REDIS_URL")

    return {
        "environment": env,
        "present": present,
        "missing": missing,
        "warnings": warnings,
        "ok": len(missing) == 0,
        "hardcoded_forbidden": True,
    }
