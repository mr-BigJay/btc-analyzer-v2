"""Bitunix parsers — execution validation fields only (Ch.3 §3.9)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unwrap(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
        return payload
    return {}


def parse_validation_snapshot(
    symbol: str,
    ticker: dict[str, Any],
    depth: dict[str, Any] | None = None,
    funding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t = _unwrap(ticker)
    d = _unwrap(depth or {})
    f = _unwrap(funding or {})

    bids = d.get("bids") or d.get("b") or []
    asks = d.get("asks") or d.get("a") or []
    best_bid = _f(bids[0][0]) if bids and isinstance(bids[0], (list, tuple)) else _f(bids[0].get("price") if bids and isinstance(bids[0], dict) else None)
    best_ask = _f(asks[0][0]) if asks and isinstance(asks[0], (list, tuple)) else _f(asks[0].get("price") if asks and isinstance(asks[0], dict) else None)
    spread = None
    if best_bid is not None and best_ask is not None:
        spread = best_ask - best_bid

    price = _f(t.get("last") or t.get("lastPrice") or t.get("price") or t.get("close"))
    return {
        "status": "OK",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "exchange": "bitunix",
        "price": price,
        "funding_rate": _f(f.get("fundingRate") or f.get("funding_rate") or t.get("fundingRate")),
        "order_book": {"bids": bids[:20], "asks": asks[:20]},
        "spread": spread,
        "open_interest": _f(t.get("openInterest") or t.get("open_interest")),
        "volume": _f(t.get("volume") or t.get("vol")),
        "source_id": str(uuid4()),
        "_required_fields": ["symbol", "timestamp"],
    }
