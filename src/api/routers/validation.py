"""Validation / backtesting API (Ch.14)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query, Request

from src.api.responses import failure, success
from src.services.validation import ValidationService

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


@router.get("/status")
def validation_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(ValidationService().status(), request_id=request_id)


@router.get("/dashboard")
def validation_dashboard(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(ValidationService().dashboard(), request_id=request_id)


@router.get("/predictions")
def validation_predictions(request: Request, limit: int = Query(50, ge=1, le=200)):
    request_id = getattr(request.state, "request_id", None)
    return success({"predictions": ValidationService().predictions(limit=limit)}, request_id=request_id)


@router.get("/paper-trades")
def validation_paper(request: Request, limit: int = Query(50, ge=1, le=200)):
    request_id = getattr(request.state, "request_id", None)
    return success({"paper_trades": ValidationService().paper_trades(limit=limit)}, request_id=request_id)


@router.post("/backtest")
def validation_backtest(request: Request, payload: dict[str, Any] = Body(...)):
    """Historical replay. Body: {closes: number[], step?, min_history?, engine_version?}."""
    request_id = getattr(request.state, "request_id", None)
    closes = payload.get("closes") or []
    if not isinstance(closes, list) or len(closes) < 40:
        return failure("closes[] with length >= 40 required", code="INVALID_SERIES", request_id=request_id, status_code=400)
    try:
        series = [float(x) for x in closes]
        result = ValidationService().backtest(
            series,
            step=int(payload.get("step") or 12),
            min_history=int(payload.get("min_history") or 30),
            engine_version=str(payload.get("engine_version") or "1.0"),
            feature_version=payload.get("feature_version"),
        )
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="BACKTEST_FAILED", request_id=request_id, status_code=500)


@router.post("/walk-forward")
def validation_walk_forward(request: Request, payload: dict[str, Any] = Body(...)):
    request_id = getattr(request.state, "request_id", None)
    closes = payload.get("closes") or []
    if not isinstance(closes, list) or len(closes) < 60:
        return failure("closes[] with length >= 60 required", code="INVALID_SERIES", request_id=request_id, status_code=400)
    try:
        result = ValidationService().walk_forward(
            [float(x) for x in closes],
            train_size=int(payload.get("train_size") or 80),
            valid_size=int(payload.get("valid_size") or 20),
            engine_version=str(payload.get("engine_version") or "1.0"),
        )
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="WALK_FORWARD_FAILED", request_id=request_id, status_code=500)


@router.post("/evaluate")
def validation_evaluate(request: Request, payload: dict[str, Any] = Body(...)):
    request_id = getattr(request.state, "request_id", None)
    outcomes = payload.get("outcomes") or []
    if not isinstance(outcomes, list):
        return failure("outcomes[] required", code="INVALID_OUTCOMES", request_id=request_id, status_code=400)
    try:
        result = ValidationService().evaluate(
            outcomes,
            engine_version=str(payload.get("engine_version") or "1.0"),
            method=str(payload.get("method") or "continuous_validation"),
            validation_period=payload.get("validation_period"),
        )
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="EVALUATE_FAILED", request_id=request_id, status_code=500)


@router.post("/approve")
def validation_approve(request: Request, payload: dict[str, Any] = Body(...)):
    request_id = getattr(request.state, "request_id", None)
    obj = payload.get("validation_object") or payload
    approver = str(payload.get("approver") or "system")
    try:
        result = ValidationService().approve(obj, approver=approver, notes=str(payload.get("notes") or ""))
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="APPROVE_FAILED", request_id=request_id, status_code=500)


@router.post("/compare")
def validation_compare(request: Request, payload: dict[str, Any] = Body(...)):
    request_id = getattr(request.state, "request_id", None)
    try:
        result = ValidationService().compare(
            list(payload.get("production_outcomes") or []),
            list(payload.get("candidate_outcomes") or []),
            horizon=str(payload.get("horizon") or "24h"),
        )
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="COMPARE_FAILED", request_id=request_id, status_code=500)
