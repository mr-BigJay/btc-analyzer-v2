"""Binance payload parsers — raw API → internal dicts (no analysis)."""

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


def parse_futures_bundle(
    symbol: str,
    premium: dict[str, Any],
    oi: dict[str, Any],
    funding_hist: list[dict[str, Any]],
    ls_ratio: list[dict[str, Any]],
    depth: dict[str, Any] | None = None,
    oi_hist: list | None = None,
    ticker: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mark = _f(premium.get("markPrice"))
    index = _f(premium.get("indexPrice"))
    last_ls = ls_ratio[-1] if ls_ratio else {}
    basis = None
    if mark is not None and index is not None and index != 0:
        basis = (mark - index) / index

    bids = (depth or {}).get("bids") or []
    asks = (depth or {}).get("asks") or []
    order_book = {
        "bids": [[_f(b[0]), _f(b[1])] for b in bids[:20]],
        "asks": [[_f(a[0]), _f(a[1])] for a in asks[:20]],
    }

    oi_value = None
    if oi_hist:
        last = oi_hist[-1]
        oi_value = _f(last.get("sumOpenInterestValue"))

    return {
        "status": "OK",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "exchange": "binance",
        "price": _f((ticker or {}).get("price")) or mark,
        "mark_price": mark,
        "index_price": index,
        "funding_rate": _f(premium.get("lastFundingRate")),
        "funding_history": funding_hist,
        "open_interest": _f(oi.get("openInterest")),
        "open_interest_value": oi_value,
        "long_short_ratio": _f(last_ls.get("longShortRatio")),
        "premium_index": _f(premium.get("lastFundingRate")),
        "basis": basis,
        "volume": None,
        "order_book": order_book,
        "liquidations": {},
        "source_id": str(uuid4()),
        "_required_fields": ["symbol", "mark_price", "timestamp"],
    }


def parse_spot_ticker(symbol: str, ticker: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "OK",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "exchange": "binance",
        "price": _f(ticker.get("lastPrice") or ticker.get("price")),
        "volume": _f(ticker.get("volume")),
        "source_id": str(uuid4()),
        "_required_fields": ["symbol", "price", "timestamp"],
    }


def parse_ohlcv(klines: list) -> list[dict[str, Any]]:
    rows = []
    for k in klines:
        if not isinstance(k, (list, tuple)) or len(k) < 6:
            continue
        rows.append(
            {
                "open_time": k[0],
                "open": _f(k[1]),
                "high": _f(k[2]),
                "low": _f(k[3]),
                "close": _f(k[4]),
                "volume": _f(k[5]),
            }
        )
    return rows
