"""Public alerts API (Ch.18 §18.7)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from src.api.responses import success
from src.api_spec.pagination import filter_items, paginate, sort_items
from src.services.events import EventService

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("")
@router.get("/")
def list_alerts(
    request: Request,
    severity: str | None = Query(None),
    asset: str | None = Query(None),
    category: str | None = Query(None),
    sort: str = Query("timestamp"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    limit: int | None = Query(None, ge=1, le=200),
):
    request_id = getattr(request.state, "request_id", None)
    rows = EventService().list_events(limit=500)
    # Only non-suppressed active-ish alerts for public feed
    rows = [r for r in rows if not r.get("suppressed")]
    rows = filter_items(rows, severity=severity, asset=asset, category=category)
    rows = sort_items(rows, sort=sort, order=order)
    if limit is not None and page == 1:
        page_size = limit
    page_rows, meta = paginate(rows, page=page, page_size=page_size)
    return success(
        {"alerts": page_rows, "pagination": meta.to_dict()},
        request_id=request_id,
    )
