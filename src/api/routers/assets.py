"""Public assets API (Ch.18 §18.7)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.responses import failure, success
from src.services.integration import IntegrationService

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.get("")
@router.get("/")
def list_assets(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(IntegrationService().list_assets(), request_id=request_id)


@router.get("/{symbol}")
def asset_metadata(symbol: str, request: Request):
    request_id = getattr(request.state, "request_id", None)
    meta = IntegrationService().asset_metadata(symbol)
    if meta is None:
        return failure(
            "Requested asset is not supported.",
            code="INVALID_SYMBOL",
            request_id=request_id,
            status_code=404,
        )
    return success(meta, request_id=request_id)
