"""Market / dashboard read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.responses import success
from src.services import AnalysisService, MarketService

router = APIRouter(prefix="/api/v1/market", tags=["market"])


@router.get("/snapshot")
def market_snapshot(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(MarketService().snapshot(), request_id=request_id)


@router.get("/patterns")
def patterns(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(AnalysisService().detect_patterns(), request_id=request_id)


@router.get("/technical")
def technical(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(AnalysisService().refresh_technical(), request_id=request_id)
