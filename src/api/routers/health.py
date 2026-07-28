"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src import __version__
from src.api.responses import success
from src.config import settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
@router.get("/api/v1/health")
def health(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(
        {
            "status": "ok",
            "version": __version__,
            "product": "decision-support-system",
            "phase": "rewrite-ch18",
            "chapter": "18-api-integration",
            "database": "postgresql" if settings.is_postgres else "sqlite",
            "redis_configured": bool(settings.redis_url),
            "timezone": settings.timezone,
        },
        request_id=request_id,
    )
