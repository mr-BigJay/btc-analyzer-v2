"""Data cleaning for feature inputs (Ch.13 §13.15). Never fabricates values."""

from __future__ import annotations

from typing import Any, Sequence


def clean_series(values: Sequence[float | None], *, forward_fill: bool = True) -> list[float | None]:
    """Clean numeric series — optional forward fill only where a prior valid exists."""
    out: list[float | None] = []
    last: float | None = None
    for v in values:
        if v is None:
            out.append(last if forward_fill else None)
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            out.append(last if forward_fill else None)
            continue
        if fv != fv or fv in (float("inf"), float("-inf")):  # NaN/Inf
            out.append(last if forward_fill else None)
            continue
        last = fv
        out.append(fv)
    return out


def drop_invalid_ohlcv(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only rows with finite OHLC; does not invent prices."""
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        try:
            o = float(row["open"])
            h = float(row["high"])
            low = float(row["low"])
            c = float(row["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if min(o, h, low, c) <= 0:
            continue
        if any(x != x or x in (float("inf"), float("-inf")) for x in (o, h, low, c)):
            continue
        cleaned.append(row)
    return cleaned


def missing_ratio(values: Sequence[Any]) -> float:
    if not values:
        return 1.0
    missing = sum(1 for v in values if v is None)
    return missing / len(values)
