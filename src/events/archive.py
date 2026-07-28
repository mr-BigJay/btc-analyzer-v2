"""Immutable event archive (Ch.16 §16.16)."""

from __future__ import annotations

from collections import deque
from typing import Any

from src.events.contracts import EventObject, EventState, utc_now_iso
from src.storage.redis_cache import redis_cache

ARCHIVE_KEY = "events:archive"
LATEST_KEY = "events:latest"
MAX_MEMORY = 500


class EventArchive:
    def __init__(self, *, maxlen: int = MAX_MEMORY) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def append(self, event: EventObject, *, persist: bool = True) -> EventObject:
        if event.state not in (EventState.ARCHIVED.value, EventState.RESOLVED.value, EventState.ACTIVE.value):
            event.transition(EventState.ARCHIVED.value)
        elif event.state != EventState.ARCHIVED.value and event.state == EventState.ACTIVE.value:
            # Keep Active for live feed; also store archive copy
            pass
        payload = event.to_dict()
        self._items.appendleft(payload)
        if persist:
            redis_cache.set(LATEST_KEY, payload, ttl_sec=86400)
            # Keep a bounded list in redis
            cached = redis_cache.get(ARCHIVE_KEY)
            lst = list(cached) if isinstance(cached, list) else []
            lst.insert(0, payload)
            redis_cache.set(ARCHIVE_KEY, lst[:MAX_MEMORY], ttl_sec=86400 * 7)
        return event

    def list(self, *, limit: int = 50, category: str | None = None, severity: str | None = None, asset: str | None = None) -> list[dict[str, Any]]:
        items = list(self._items)
        if not items:
            cached = redis_cache.get(ARCHIVE_KEY)
            items = list(cached) if isinstance(cached, list) else []
        out = []
        for row in items:
            if category and row.get("category") != category:
                continue
            if severity and row.get("severity") != severity:
                continue
            if asset and str(row.get("asset") or "").upper() != asset.upper():
                continue
            out.append(row)
            if len(out) >= limit:
                break
        return out

    def get(self, event_id: str) -> dict[str, Any] | None:
        for row in self.list(limit=MAX_MEMORY):
            if row.get("event_id") == event_id:
                return row
        return None

    def resolve(self, event_id: str) -> dict[str, Any] | None:
        row = self.get(event_id)
        if not row:
            return None
        obj = EventObject.from_dict(row)
        obj.transition(EventState.RESOLVED.value)
        obj.resolved_at = utc_now_iso()
        self.append(obj, persist=True)
        return obj.to_dict()


event_archive = EventArchive()
