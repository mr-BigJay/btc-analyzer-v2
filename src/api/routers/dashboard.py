"""Dashboard UX API (Ch.17)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Request

from src.api.responses import failure, success
from src.services.dashboard import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/status")
def dashboard_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(DashboardService().status(), request_id=request_id)


@router.get("/view")
def dashboard_view(request: Request):
    """Full dashboard view model for the UI shell."""
    request_id = getattr(request.state, "request_id", None)
    try:
        return success(DashboardService().view(use_cache=True), request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="DASHBOARD_VIEW_FAILED", request_id=request_id, status_code=500)


@router.post("/view")
def dashboard_view_from_payload(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    """Build a dashboard view from an explicit analytical payload (tests / offline)."""
    request_id = getattr(request.state, "request_id", None)
    try:
        result = DashboardService().view(
            ai_report=payload.get("ai_report"),
            analysis=payload.get("analysis"),
            intelligence=payload.get("intelligence"),
            scoring=payload.get("scoring"),
            risk=payload.get("risk") or payload.get("risk_object"),
            events=payload.get("events"),
            snapshot=payload.get("snapshot"),
            historical=payload.get("historical"),
            connection_ok=bool(payload.get("connection_ok", True)),
            partial_services=bool(payload.get("partial_services", False)),
            maintenance=bool(payload.get("maintenance", False)),
            use_cache=bool(payload.get("use_cache", False)),
        )
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="DASHBOARD_BUILD_FAILED", request_id=request_id, status_code=500)


@router.get("/preferences")
def dashboard_preferences(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(DashboardService().preferences(), request_id=request_id)


@router.put("/preferences")
@router.post("/preferences")
def dashboard_update_preferences(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    request_id = getattr(request.state, "request_id", None)
    # Personalization never affects analytical results — presentation only
    prefs = payload.get("preferences") or payload
    return success(DashboardService().update_preferences(prefs), request_id=request_id)
