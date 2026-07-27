"""Collection API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.responses import failure, success
from src.config import settings
from src.services import CollectionService

router = APIRouter(prefix="/api/v1/collection", tags=["collection"])


@router.get("/status")
def collection_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    svc = CollectionService()
    return success(
        {
            "enabled": {
                "binance": settings.binance_futures_enabled,
                "deribit": settings.deribit_enabled,
                "coinex": settings.coinex_enabled,
                "bitunix": settings.bitunix_enabled,
            },
            **svc.status(),
        },
        request_id=request_id,
    )


@router.post("/run")
def collection_run(request: Request):
    request_id = getattr(request.state, "request_id", None)
    try:
        result = CollectionService().run_full()
        return success(result.to_dict(), request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="COLLECTION_FAILED", request_id=request_id, status_code=500)
