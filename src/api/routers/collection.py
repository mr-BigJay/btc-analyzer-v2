"""Collection API endpoints (Ch.3 / Ch.12)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

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


@router.get("/health")
def collection_health(request: Request):
    """Per-collector health (Ch.12 §12.18)."""
    from src.collectors.health import health_monitor

    request_id = getattr(request.state, "request_id", None)
    return success(health_monitor.snapshot(), request_id=request_id)


@router.get("/events")
def collection_events(request: Request, limit: int = Query(20, ge=1, le=100)):
    """Recent internal market events (Ch.12 §12.15)."""
    from src.collectors.events import event_bus

    request_id = getattr(request.state, "request_id", None)
    return success({"events": event_bus.recent(limit=limit)}, request_id=request_id)


@router.get("/quarantine")
def collection_quarantine(request: Request, limit: int = Query(50, ge=1, le=200)):
    """Quarantined invalid records (Ch.12 §12.10)."""
    from src.collectors.quarantine import quarantine_store

    request_id = getattr(request.state, "request_id", None)
    return success(
        {"count": quarantine_store.count(), "items": quarantine_store.list(limit=limit)},
        request_id=request_id,
    )


@router.get("/symbols")
def collection_symbols(request: Request):
    """Symbol registry mappings (Ch.12 §12.16)."""
    from src.collectors.symbols import symbol_registry

    request_id = getattr(request.state, "request_id", None)
    return success({"mappings": symbol_registry.list_mappings()}, request_id=request_id)


@router.post("/run")
def collection_run(request: Request):
    request_id = getattr(request.state, "request_id", None)
    try:
        result = CollectionService().run_full()
        return success(result.to_dict(), request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="COLLECTION_FAILED", request_id=request_id, status_code=500)


@router.post("/run/{collector_type}")
def collection_run_typed(collector_type: str, request: Request):
    """Run a typed collector family: spot|futures|options|volatility|macro."""
    request_id = getattr(request.state, "request_id", None)
    try:
        result = CollectionService().run_typed(collector_type)
        return success(result, request_id=request_id)
    except ValueError as exc:
        return failure(str(exc), code="UNKNOWN_COLLECTOR_TYPE", request_id=request_id, status_code=400)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="COLLECTION_FAILED", request_id=request_id, status_code=500)


@router.post("/backfill")
def collection_backfill(
    request: Request,
    timeframe: str = Query("1h"),
    limit: int = Query(200, ge=1, le=1500),
):
    """Historical OHLCV backfill isolated from live streams (Ch.12 §12.17)."""
    request_id = getattr(request.state, "request_id", None)
    try:
        result = CollectionService().backfill(timeframe=timeframe, limit=limit)
        return success(result, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        return failure(str(exc), code="BACKFILL_FAILED", request_id=request_id, status_code=500)
