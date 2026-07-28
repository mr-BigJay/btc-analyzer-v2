"""Public reports API (Ch.18 §18.7)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from src.api.responses import failure, success
from src.api_spec.validation import validate_symbol
from src.services.reports import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/daily/{symbol}")
def daily_outlook(
    symbol: str,
    request: Request,
    audience: str = Query("professional"),
    language: str = Query("en"),
):
    request_id = getattr(request.state, "request_id", None)
    ok, err = validate_symbol(symbol)
    if not ok:
        return failure(err or "Invalid symbol", code="INVALID_SYMBOL", request_id=request_id, status_code=404)
    try:
        # ReportService uses configured default symbol via upstream; attach requested symbol in response
        data = ReportService().daily_outlook(audience=audience, language=language, persist=False)
        if isinstance(data, dict):
            meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
            meta = dict(meta)
            meta["symbol"] = symbol.upper()
            data = {**data, "metadata": meta, "symbol": symbol.upper()}
        return success(data, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="REPORT_FAILED", request_id=request_id, status_code=500)


@router.get("/intraday/{symbol}")
def intraday_plan(
    symbol: str,
    request: Request,
    audience: str = Query("professional"),
):
    request_id = getattr(request.state, "request_id", None)
    ok, err = validate_symbol(symbol)
    if not ok:
        return failure(err or "Invalid symbol", code="INVALID_SYMBOL", request_id=request_id, status_code=404)
    try:
        data = ReportService().trading_plan(audience=audience)
        if isinstance(data, dict):
            data = {**data, "symbol": symbol.upper()}
        return success(data, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="REPORT_FAILED", request_id=request_id, status_code=500)
