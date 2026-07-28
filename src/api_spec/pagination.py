"""Pagination, sorting, filtering helpers (Ch.18 §18.15–§18.16)."""

from __future__ import annotations

from typing import Any, Callable, Sequence

from src.api_spec.contracts import PaginationMeta


def paginate(
    items: Sequence[Any],
    *,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Any], PaginationMeta]:
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 200))
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 0
    start = (page - 1) * page_size
    end = start + page_size
    slice_ = list(items[start:end])
    meta = PaginationMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages)
    return slice_, meta


def sort_items(
    items: list[dict[str, Any]],
    *,
    sort: str | None = None,
    order: str = "desc",
) -> list[dict[str, Any]]:
    if not sort:
        return items
    reverse = str(order).lower() != "asc"

    def key_fn(row: dict[str, Any]):
        val = row.get(sort)
        return (val is None, val)

    try:
        return sorted(items, key=key_fn, reverse=reverse)
    except TypeError:
        return items


def filter_items(
    items: list[dict[str, Any]],
    *,
    severity: str | None = None,
    asset: str | None = None,
    regime: str | None = None,
    category: str | None = None,
    predicate: Callable[[dict[str, Any]], bool] | None = None,
) -> list[dict[str, Any]]:
    out = []
    for row in items:
        if severity and str(row.get("severity") or "").lower() != severity.lower():
            continue
        if asset and str(row.get("asset") or row.get("symbol") or "").upper() != asset.upper():
            continue
        if regime and str(row.get("regime") or row.get("market_regime") or "") != regime:
            continue
        if category and str(row.get("category") or "") != category:
            continue
        if predicate and not predicate(row):
            continue
        out.append(row)
    return out
