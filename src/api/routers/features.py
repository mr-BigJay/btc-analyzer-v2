"""Feature engineering API (Ch.13)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from src.api.responses import failure, success
from src.services.features import FeatureService

router = APIRouter(prefix="/api/v1/features", tags=["features"])


@router.get("/status")
def features_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(FeatureService().status(), request_id=request_id)


@router.get("/latest")
def features_latest(
    request: Request,
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
):
    request_id = getattr(request.state, "request_id", None)
    data = FeatureService().latest(symbol, timeframe)
    if data is None:
        return failure("No feature set in store", code="FEATURES_EMPTY", request_id=request_id, status_code=404)
    return success(data, request_id=request_id)


@router.post("/engineer")
def features_engineer(
    request: Request,
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    multi_timeframe: bool = Query(False),
):
    request_id = getattr(request.state, "request_id", None)
    try:
        data = FeatureService().engineer(
            symbol=symbol,
            timeframe=timeframe,
            persist=True,
            multi_timeframe=multi_timeframe,
        )
        return success(data, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="FEATURE_ENGINE_FAILED", request_id=request_id, status_code=500)


@router.get("/quarantine")
def features_quarantine(request: Request, limit: int = Query(50, ge=1, le=200)):
    from src.features.validation import feature_quarantine

    request_id = getattr(request.state, "request_id", None)
    return success(
        {"count": feature_quarantine.count(), "items": feature_quarantine.list(limit=limit)},
        request_id=request_id,
    )
