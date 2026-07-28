"""Request validation helpers (Ch.18 §18.20)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from src.config import settings

SYMBOL_RE = re.compile(r"^[A-Z0-9]{3,20}$")


def supported_symbols() -> list[str]:
    raw = settings.supported_assets or settings.binance_symbol or "BTCUSDT"
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def validate_symbol(symbol: str | None) -> tuple[bool, str | None]:
    if not symbol:
        return False, "Symbol is required"
    sym = symbol.strip().upper()
    if not SYMBOL_RE.match(sym):
        return False, "Invalid symbol format"
    allowed = supported_symbols()
    if allowed and sym not in allowed:
        return False, "Requested asset is not supported."
    return True, None


def validate_utc_timestamp(value: str | None) -> tuple[bool, str | None]:
    if value is None or value == "":
        return True, None
    try:
        s = str(value).replace("Z", "+00:00")
        datetime.fromisoformat(s)
        return True, None
    except ValueError:
        return False, "Invalid timestamp format; use ISO-8601 UTC"


def validate_limit(limit: int | None, *, default: int = 50, max_limit: int = 200) -> int:
    if limit is None:
        return default
    return max(1, min(int(limit), max_limit))


def validate_page(page: int | None, page_size: int | None) -> tuple[int, int]:
    p = max(1, int(page or 1))
    ps = validate_limit(page_size, default=50, max_limit=200)
    return p, ps


def validate_query_params(params: dict[str, Any]) -> list[str]:
    """Return list of validation error messages (empty = ok)."""
    errors: list[str] = []
    if "symbol" in params and params["symbol"] is not None:
        ok, err = validate_symbol(str(params["symbol"]))
        if not ok:
            errors.append(err or "INVALID_SYMBOL")
    for key in ("from", "to", "timestamp"):
        if key in params and params[key]:
            ok, err = validate_utc_timestamp(str(params[key]))
            if not ok:
                errors.append(err or f"Invalid {key}")
    if "limit" in params and params["limit"] is not None:
        try:
            n = int(params["limit"])
            if n < 1 or n > 500:
                errors.append("limit out of range (1–500)")
        except (TypeError, ValueError):
            errors.append("limit must be an integer")
    return errors
