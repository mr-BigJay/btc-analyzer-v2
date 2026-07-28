"""Risk Management API (Ch.15)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Request

from src.api.responses import failure, success
from src.services.risk import RiskService

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("/status")
def risk_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(RiskService().status(), request_id=request_id)


@router.get("/latest")
def risk_latest(request: Request):
    request_id = getattr(request.state, "request_id", None)
    latest = RiskService().latest()
    if latest is None:
        return failure("No cached risk object", code="RISK_NOT_FOUND", request_id=request_id, status_code=404)
    return success(latest, request_id=request_id)


@router.post("/evaluate")
def risk_evaluate(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    """Evaluate execution risk. Body may include decision, intelligence, analysis, flags."""
    request_id = getattr(request.state, "request_id", None)
    try:
        result = RiskService().evaluate(
            decision=payload.get("decision") or {},
            intelligence=payload.get("intelligence") or {},
            analysis=payload.get("analysis") or {},
            context=payload.get("context") or {},
            macro_event=bool(payload.get("macro_event") or False),
            near_options_expiry=bool(payload.get("near_options_expiry") or False),
            exchange_degraded=bool(payload.get("exchange_degraded") or False),
            unresolved_validation=bool(payload.get("unresolved_validation") or False),
            persist=bool(payload.get("persist", True)),
        )
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="RISK_EVAL_FAILED", request_id=request_id, status_code=500)


@router.post("/apply-plan")
def risk_apply_plan(request: Request, payload: dict[str, Any] = Body(...)):
    """Apply Risk Object controls to a trading plan dict (AI cannot bypass)."""
    request_id = getattr(request.state, "request_id", None)
    plan = payload.get("trading_plan") or payload.get("plan")
    risk = payload.get("risk_object") or payload.get("risk")
    if not isinstance(plan, dict) or not isinstance(risk, dict):
        return failure(
            "trading_plan and risk_object objects required",
            code="INVALID_PAYLOAD",
            request_id=request_id,
            status_code=400,
        )
    try:
        result = RiskService().apply_to_trading_plan(plan, risk)
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="RISK_APPLY_FAILED", request_id=request_id, status_code=500)
