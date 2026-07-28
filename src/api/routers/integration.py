"""API integration endpoints — auth, webhooks, catalog, metrics (Ch.18)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Header, Request

from src.api.responses import failure, success
from src.api_spec.idempotency import lookup, store
from src.services.integration import IntegrationService

router = APIRouter(prefix="/api/v1/integration", tags=["integration"])


@router.get("/status")
def integration_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(IntegrationService().status(), request_id=request_id)


@router.get("/metrics")
def integration_metrics(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(IntegrationService().metrics(), request_id=request_id)


@router.post("/auth/token")
def issue_token(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    request_id = getattr(request.state, "request_id", None)
    try:
        data = IntegrationService().issue_token(
            subject=str(payload.get("subject") or "client"),
            role=payload.get("role"),
            api_key=payload.get("api_key") or request.headers.get("X-API-Key"),
        )
        return success(data, request_id=request_id, status_code=201)
    except PermissionError as exc:
        return failure(str(exc), code="UNAUTHORIZED", request_id=request_id, status_code=401)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="TOKEN_FAILED", request_id=request_id, status_code=500)


@router.post("/auth/refresh")
def refresh_token(request: Request, payload: dict[str, Any] = Body(...)):
    request_id = getattr(request.state, "request_id", None)
    token = str(payload.get("refresh_token") or "")
    if not token:
        return failure("refresh_token required", code="VALIDATION_ERROR", request_id=request_id, status_code=422)
    try:
        return success(IntegrationService().refresh_token(token), request_id=request_id)
    except PermissionError as exc:
        return failure(str(exc), code="UNAUTHORIZED", request_id=request_id, status_code=401)


@router.get("/webhooks")
def list_webhooks(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success({"webhooks": IntegrationService().list_webhooks()}, request_id=request_id)


@router.post("/webhooks")
def register_webhook(
    request: Request,
    payload: dict[str, Any] = Body(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    request_id = getattr(request.state, "request_id", None)
    route = "POST /api/v1/integration/webhooks"
    cached = lookup(idempotency_key, route=route)
    if cached:
        return success(cached.get("body"), request_id=request_id, status_code=int(cached.get("status_code") or 200))

    url = str(payload.get("url") or "")
    if not url.startswith("https://") and not url.startswith("http://"):
        return failure("url must be http(s)", code="VALIDATION_ERROR", request_id=request_id, status_code=422)
    try:
        data = IntegrationService().register_webhook(
            url=url,
            events=list(payload.get("events") or []),
            secret=str(payload.get("secret") or ""),
        )
        store(idempotency_key, route=route, response=data, status_code=201)
        return success(data, request_id=request_id, status_code=201)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="WEBHOOK_FAILED", request_id=request_id, status_code=500)


@router.delete("/webhooks/{subscription_id}")
def delete_webhook(subscription_id: str, request: Request):
    request_id = getattr(request.state, "request_id", None)
    ok = IntegrationService().delete_webhook(subscription_id)
    if not ok:
        return failure("Webhook not found", code="NOT_FOUND", request_id=request_id, status_code=404)
    return success({"deleted": True, "subscription_id": subscription_id}, request_id=request_id)


@router.post("/webhooks/dispatch")
def dispatch_webhook(request: Request, payload: dict[str, Any] = Body(...)):
    request_id = getattr(request.state, "request_id", None)
    event = str(payload.get("event") or "")
    if not event:
        return failure("event required", code="VALIDATION_ERROR", request_id=request_id, status_code=422)
    results = IntegrationService().dispatch_webhook(
        event,
        dict(payload.get("data") or {}),
        dry_run=bool(payload.get("dry_run", True)),
    )
    return success({"deliveries": results}, request_id=request_id, status_code=202)
