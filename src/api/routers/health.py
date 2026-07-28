"""Health / ready / live endpoints (Ch.5 + Ch.20 probes)."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from src import __version__
from src.api.responses import success, utc_now_iso
from src.config import settings
from src.deploy.environments import resolve_environment
from src.deploy.probes import health_detailed, liveness, readiness

router = APIRouter(tags=["health"])


@router.get("/api/health")
@router.get("/api/v1/health")
@router.get("/health")
def health(request: Request):
    request_id = getattr(request.state, "request_id", None)
    detailed = health_detailed()
    return success(
        {
            "status": detailed.get("status", "ok"),
            "version": __version__,
            "product": "decision-support-system",
            "phase": "rewrite-ch22",
            "chapter": "22-testing-qa",
            "database": "postgresql" if settings.is_postgres else "sqlite",
            "redis_configured": bool(settings.redis_url),
            "timezone": settings.timezone,
            "environment": resolve_environment(),
            "checks": detailed.get("ready", {}).get("checks"),
        },
        request_id=request_id,
        status_code=200 if detailed.get("ok") else 503,
    )


@router.get("/ready")
@router.get("/api/v1/ready")
def ready(request: Request):
    request_id = getattr(request.state, "request_id", None)
    data = readiness()
    body = {
        "status": "success" if data.get("ok") else "error",
        "timestamp": utc_now_iso(),
        "request_id": request_id,
        "data": data,
    }
    return JSONResponse(content=body, status_code=200 if data.get("ok") else 503)


@router.get("/live")
@router.get("/api/v1/live")
def live(request: Request):
    request_id = getattr(request.state, "request_id", None)
    data = liveness()
    return success(data, request_id=request_id)
