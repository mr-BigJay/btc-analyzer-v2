"""Internal event bus for normalized market events (Ch.12 §12.15).

Publishers remain unaware of subscribers (loose coupling).
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

Subscriber = Callable[["MarketEvent"], None]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class MarketEvent:
    event: str
    asset: str
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "asset": self.asset,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "source": self.source,
        }


class EventBus:
    """In-process pub/sub for collection → analysis / cache / alerts."""

    def __init__(self, *, history_size: int = 200) -> None:
        self._subs: dict[str, list[Subscriber]] = defaultdict(list)
        self._history: deque[MarketEvent] = deque(maxlen=history_size)
        self._lock = threading.RLock()
        self._seq = 0

    def subscribe(self, event_name: str, handler: Subscriber) -> None:
        with self._lock:
            self._subs[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Subscriber) -> None:
        with self._lock:
            handlers = self._subs.get(event_name) or []
            self._subs[event_name] = [h for h in handlers if h is not handler]

    def publish(
        self,
        event_name: str,
        *,
        asset: str,
        payload: dict[str, Any] | None = None,
        source: str | None = None,
        timestamp: str | None = None,
    ) -> MarketEvent:
        evt = MarketEvent(
            event=event_name,
            asset=asset.upper(),
            timestamp=timestamp or _utc_now(),
            payload=payload or {},
            source=source,
        )
        with self._lock:
            self._seq += 1
            self._history.append(evt)
            handlers = list(self._subs.get(event_name, []))
            # Wildcard subscribers
            handlers.extend(self._subs.get("*", []))
        for handler in handlers:
            try:
                handler(evt)
            except Exception:  # noqa: BLE001
                logger.exception("event subscriber failed event=%s", event_name)
        return evt

    def recent(self, *, limit: int = 20, event_name: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._history)
        if event_name:
            items = [e for e in items if e.event == event_name]
        return [e.to_dict() for e in items[-limit:]]

    def clear(self) -> None:
        with self._lock:
            self._history.clear()
            self._subs.clear()
            self._seq = 0


# Process singleton
event_bus = EventBus()
