"""Rate limiting and burst suppression (Ch.16 §16.15). Critical bypasses."""

from __future__ import annotations

import time
from typing import Any

from src.events.contracts import EventObject, EventSeverity, SEVERITY_RANK
from src.storage.redis_cache import redis_cache

RATE_KEY = "events:rate_limit"
MAX_PER_ASSET_WINDOW = 8
ASSET_WINDOW_SEC = 600
MIN_INTERVAL_IDENTICAL_SEC = 120
BURST_WINDOW_SEC = 60
BURST_MAX = 4


def _store() -> dict[str, Any]:
    raw = redis_cache.get(RATE_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def apply_rate_limits(
    events: list[EventObject],
    *,
    memory: dict[str, Any] | None = None,
    persist: bool = True,
) -> list[EventObject]:
    store = memory if memory is not None else _store()
    now = time.time()
    out: list[EventObject] = []

    for event in events:
        if event.suppressed:
            out.append(event)
            continue
        if event.severity == EventSeverity.CRITICAL.value:
            # Critical bypasses standard limits
            _record(store, event, now)
            out.append(event)
            continue

        asset_key = f"asset:{event.asset.upper()}"
        asset_hits = [t for t in (store.get(asset_key) or []) if now - float(t) <= ASSET_WINDOW_SEC]
        if len(asset_hits) >= MAX_PER_ASSET_WINDOW:
            event.suppressed = True
            event.suppression_reason = f"Rate limit: max {MAX_PER_ASSET_WINDOW} alerts/{ASSET_WINDOW_SEC}s per asset"
            out.append(event)
            continue

        identical_key = f"id:{event.fingerprint or event.type}:{event.asset}"
        last_identical = float(store.get(identical_key) or 0)
        if last_identical and now - last_identical < MIN_INTERVAL_IDENTICAL_SEC:
            # Allow if severity increased vs stored
            prev_sev = SEVERITY_RANK.get(str(store.get(f"{identical_key}:sev") or ""), 0)
            if SEVERITY_RANK.get(event.severity, 0) <= prev_sev:
                event.suppressed = True
                event.suppression_reason = f"Min interval {MIN_INTERVAL_IDENTICAL_SEC}s for identical events"
                out.append(event)
                continue

        burst_key = "burst:global"
        burst_hits = [t for t in (store.get(burst_key) or []) if now - float(t) <= BURST_WINDOW_SEC]
        if len(burst_hits) >= BURST_MAX and SEVERITY_RANK.get(event.severity, 0) < 3:
            event.suppressed = True
            event.suppression_reason = "Burst suppression active"
            out.append(event)
            continue

        _record(store, event, now)
        out.append(event)

    if persist and memory is None:
        redis_cache.set(RATE_KEY, store, ttl_sec=86400)
    return out


def _record(store: dict[str, Any], event: EventObject, now: float) -> None:
    asset_key = f"asset:{event.asset.upper()}"
    hits = [t for t in (store.get(asset_key) or []) if now - float(t) <= ASSET_WINDOW_SEC]
    hits.append(now)
    store[asset_key] = hits
    identical_key = f"id:{event.fingerprint or event.type}:{event.asset}"
    store[identical_key] = now
    store[f"{identical_key}:sev"] = event.severity
    burst = [t for t in (store.get("burst:global") or []) if now - float(t) <= BURST_WINDOW_SEC]
    burst.append(now)
    store["burst:global"] = burst
