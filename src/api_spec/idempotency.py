"""Idempotency-Key handling for state-changing endpoints (Ch.18 §18.19)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.storage.redis_cache import redis_cache

IDEMPOTENCY_PREFIX = "api:idempotency:"
TTL_SEC = 86400


def _key(idempotency_key: str, route: str) -> str:
    digest = hashlib.sha256(f"{route}:{idempotency_key}".encode()).hexdigest()[:32]
    return f"{IDEMPOTENCY_PREFIX}{digest}"


def lookup(idempotency_key: str | None, *, route: str) -> dict[str, Any] | None:
    if not idempotency_key:
        return None
    cached = redis_cache.get(_key(idempotency_key, route))
    return dict(cached) if isinstance(cached, dict) else None


def store(idempotency_key: str | None, *, route: str, response: dict[str, Any], status_code: int = 200) -> None:
    if not idempotency_key:
        return
    redis_cache.set(
        _key(idempotency_key, route),
        {"status_code": status_code, "body": response},
        ttl_sec=TTL_SEC,
    )


def fingerprint_body(body: Any) -> str:
    raw = json.dumps(body, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()
