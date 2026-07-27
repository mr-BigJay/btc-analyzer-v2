"""In-memory cache for frequently accessed datasets (Ch.3 §3.12)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CacheEntry:
    key: str
    value: Any
    updated_at: str = field(default_factory=_utc_now)


class MemoryCache:
    """Process-local hot cache.

    Examples: latest funding, current OI, option chain, order book, daily outlook.
    """

    KEYS = (
        "latest_funding_rate",
        "current_open_interest",
        "latest_option_chain",
        "current_order_book",
        "active_daily_outlook",
        "latest_mark_price",
        "bitunix_validation_snapshot",
    )

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._store: dict[str, CacheEntry] = {}

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = CacheEntry(key=key, value=value)

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            return entry.value if entry else None

    def get_entry(self, key: str) -> CacheEntry | None:
        with self._lock:
            return self._store.get(key)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                k: {"value": e.value, "updated_at": e.updated_at}
                for k, e in self._store.items()
            }


# Process singleton used by CentralRepository / collectors
global_cache = MemoryCache()
