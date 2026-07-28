"""Service health / ready / live probes (Ch.20 §20.12)."""

from __future__ import annotations

from typing import Any

from src import __version__
from src.config import settings
from src.deploy.environments import resolve_environment


def check_database() -> dict[str, Any]:
    try:
        from sqlalchemy import text

        from src.db.session import get_session

        session = get_session()
        try:
            session.execute(text("SELECT 1"))
            return {"ok": True, "detail": "connected"}
        finally:
            session.close()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)[:200]}


def check_redis() -> dict[str, Any]:
    if not settings.redis_url:
        return {"ok": True, "detail": "memory-fallback", "optional": True}
    try:
        from src.storage.redis_cache import redis_cache

        redis_cache.set("deploy:healthping", "1", ttl_sec=30)
        val = redis_cache.get("deploy:healthping")
        ok = val in ("1", 1, True) or val is not None
        return {"ok": bool(ok), "detail": "connected"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": str(exc)[:200]}


def liveness() -> dict[str, Any]:
    """Process is up — no dependency checks."""
    return {
        "status": "live",
        "ok": True,
        "version": __version__,
        "environment": resolve_environment(),
    }


def readiness() -> dict[str, Any]:
    """Ready to serve traffic — DB required; Redis preferred."""
    db = check_database()
    redis = check_redis()
    ok = bool(db.get("ok"))
    # Redis optional in dev; if configured URL exists and check fails, not ready
    if settings.redis_url and not redis.get("ok"):
        ok = False
    return {
        "status": "ready" if ok else "not_ready",
        "ok": ok,
        "version": __version__,
        "checks": {"database": db, "redis": redis},
        "environment": resolve_environment(),
    }


def health_detailed() -> dict[str, Any]:
    ready = readiness()
    live = liveness()
    return {
        "status": "ok" if ready["ok"] else "degraded",
        "ok": ready["ok"],
        "live": live,
        "ready": ready,
        "version": __version__,
        "product": "decision-support-system",
        "timezone": settings.timezone,
        "database": "postgresql" if settings.is_postgres else "sqlite",
        "redis_configured": bool(settings.redis_url),
        "environment": resolve_environment(),
    }
