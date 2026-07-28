"""Observability API (Ch.21)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from src.api.responses import success
from src.services.observability import ObservabilityService

router = APIRouter(prefix="/api/v1/observability", tags=["observability"])


@router.get("/status")
def observability_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(ObservabilityService().status(), request_id=request_id)


@router.get("/object")
def observability_object(request: Request, service: str = "api"):
    request_id = getattr(request.state, "request_id", None)
    return success(ObservabilityService().observability_object(service), request_id=request_id)


@router.get("/metrics")
def observability_metrics(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(ObservabilityService().metrics(), request_id=request_id)


@router.get("/slos")
def observability_slos(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(ObservabilityService().slos(), request_id=request_id)


@router.get("/alerts")
def observability_alerts(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(ObservabilityService().alerts(), request_id=request_id)


@router.get("/traces")
def observability_traces(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    trace_id: str | None = None,
    correlation_id: str | None = None,
):
    request_id = getattr(request.state, "request_id", None)
    return success(
        ObservabilityService().traces(limit=limit, trace_id=trace_id, correlation_id=correlation_id),
        request_id=request_id,
    )


@router.get("/dashboard")
def observability_dashboard(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(ObservabilityService().dashboard(), request_id=request_id)


@router.get("/anomalies")
def observability_anomalies(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(ObservabilityService().anomalies(), request_id=request_id)


@router.get("/capacity")
def observability_capacity(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(ObservabilityService().capacity(), request_id=request_id)
