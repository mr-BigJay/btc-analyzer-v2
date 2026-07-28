"""Alert deduplication (Ch.16 §16.9)."""

from __future__ import annotations

import time
from typing import Any

from src.events.contracts import EventObject, EventSeverity, SEVERITY_RANK
from src.storage.redis_cache import redis_cache

DEDUP_KEY = "events:dedupe"
DEFAULT_WINDOW_SEC = 1800  # 30 minutes


def _store() -> dict[str, Any]:
    raw = redis_cache.get(DEDUP_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def is_duplicate(
    event: EventObject,
    *,
    window_sec: int = DEFAULT_WINDOW_SEC,
    memory: dict[str, Any] | None = None,
) -> tuple[bool, str | None]:
    """Suppress duplicate by type+asset+fingerprint within window; severity upgrades escape."""
    store = memory if memory is not None else _store()
    fp = event.fingerprint or f"{event.category}|{event.type}|{event.asset}".lower()
    key = fp
    now = time.time()
    prev = store.get(key)
    if not isinstance(prev, dict):
        return False, None
    age = now - float(prev.get("ts") or 0)
    if age > window_sec:
        return False, None
    prev_sev = SEVERITY_RANK.get(str(prev.get("severity") or ""), 0)
    cur_sev = SEVERITY_RANK.get(event.severity, 0)
    # Meaningful severity upgrade → allow
    if cur_sev > prev_sev:
        return False, None
    # State change to Resolved always allowed elsewhere
    return True, str(prev.get("event_id") or "")


def remember(
    event: EventObject,
    *,
    memory: dict[str, Any] | None = None,
    persist: bool = True,
) -> None:
    store = memory if memory is not None else _store()
    fp = event.fingerprint or f"{event.category}|{event.type}|{event.asset}".lower()
    store[fp] = {
        "event_id": event.event_id,
        "severity": event.severity,
        "state": event.state,
        "ts": time.time(),
        "type": event.type,
        "asset": event.asset,
    }
    if persist and memory is None:
        redis_cache.set(DEDUP_KEY, store, ttl_sec=86400)


def apply_deduplication(
    events: list[EventObject],
    *,
    window_sec: int = DEFAULT_WINDOW_SEC,
    memory: dict[str, Any] | None = None,
    persist: bool = True,
) -> list[EventObject]:
    """Mark duplicates as suppressed; remember non-duplicates."""
    out: list[EventObject] = []
    local = memory if memory is not None else _store()
    for event in events:
        # Critical always remembered but never suppressed as duplicate of weaker
        dup, prior_id = is_duplicate(event, window_sec=window_sec, memory=local)
        if dup and event.severity != EventSeverity.CRITICAL.value:
            event.suppressed = True
            event.duplicate_of = prior_id
            event.suppression_reason = f"Duplicate within {window_sec}s window"
            out.append(event)
            continue
        remember(event, memory=local, persist=False)
        out.append(event)
    if persist and memory is None:
        redis_cache.set(DEDUP_KEY, local, ttl_sec=86400)
    return out
