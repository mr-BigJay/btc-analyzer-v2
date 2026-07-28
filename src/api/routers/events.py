"""Alerting & Event Processing API (Ch.16)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query, Request

from src.api.responses import failure, success
from src.services.events import EventService

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/status")
def events_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(EventService().status(), request_id=request_id)


@router.get("/analytics")
def events_analytics(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(EventService().analytics(), request_id=request_id)


@router.get("/list")
def events_list(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    category: str | None = None,
    severity: str | None = None,
    asset: str | None = None,
):
    request_id = getattr(request.state, "request_id", None)
    rows = EventService().list_events(limit=limit, category=category, severity=severity, asset=asset)
    return success({"events": rows, "count": len(rows)}, request_id=request_id)


@router.get("/dashboard")
def events_dashboard(request: Request, limit: int = Query(30, ge=1, le=100)):
    request_id = getattr(request.state, "request_id", None)
    return success({"cards": EventService().dashboard_cards(limit=limit)}, request_id=request_id)


@router.post("/process")
def events_process(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    """Process a market/AI snapshot through the event lifecycle."""
    request_id = getattr(request.state, "request_id", None)
    try:
        result = EventService().process(
            payload.get("snapshot") or payload,
            asset=payload.get("asset") or payload.get("symbol") or "BTCUSDT",
            previous=payload.get("previous"),
            system=payload.get("system"),
            persist=bool(payload.get("persist", True)),
            notify=bool(payload.get("notify", True)),
            skip_external=bool(payload.get("skip_external", True)),
        )
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="EVENT_PROCESS_FAILED", request_id=request_id, status_code=500)


@router.post("/system")
def events_system(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    request_id = getattr(request.state, "request_id", None)
    try:
        result = EventService().system_alert(
            asset=str(payload.get("asset") or "BTCUSDT"),
            collector_failure=bool(payload.get("collector_failure")),
            exchange_degraded=bool(payload.get("exchange_degraded")),
            message=str(payload.get("message") or ""),
            persist=bool(payload.get("persist", True)),
            notify=bool(payload.get("notify", True)),
            skip_external=bool(payload.get("skip_external", True)),
        )
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="SYSTEM_EVENT_FAILED", request_id=request_id, status_code=500)


@router.post("/resolve")
def events_resolve(request: Request, payload: dict[str, Any] = Body(...)):
    request_id = getattr(request.state, "request_id", None)
    event_id = str(payload.get("event_id") or "")
    if not event_id:
        return failure("event_id required", code="INVALID_PAYLOAD", request_id=request_id, status_code=400)
    row = EventService().resolve(event_id)
    if row is None:
        return failure("event not found", code="EVENT_NOT_FOUND", request_id=request_id, status_code=404)
    return success(row, request_id=request_id)


@router.post("/replay")
def events_replay(request: Request, payload: dict[str, Any] = Body(...)):
    request_id = getattr(request.state, "request_id", None)
    snapshots = payload.get("snapshots") or []
    if not isinstance(snapshots, list) or not snapshots:
        return failure("snapshots[] required", code="INVALID_PAYLOAD", request_id=request_id, status_code=400)
    try:
        result = EventService().replay(snapshots, asset=str(payload.get("asset") or "BTCUSDT"))
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="REPLAY_FAILED", request_id=request_id, status_code=500)
