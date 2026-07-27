"""WebSocket hub — live price, alerts, dashboard updates (Ch.5 §5.5 / §5.9)."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from src.cache.keys import CacheKeys
from src.logging_setup import get_logger
from src.storage.redis_cache import redis_cache

log = get_logger("websocket")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class WebSocketHub:
    """In-process fan-out hub for dashboard clients."""

    clients: set[WebSocket] = field(default_factory=set)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.clients.add(websocket)
        log.info("WS client connected (n={})", len(self.clients))
        # Push hot cache snapshot on connect
        await self.send_personal(
            websocket,
            {
                "type": "snapshot",
                "timestamp": _utc(),
                "data": {
                    "mark_price": redis_cache.get(CacheKeys.LATEST_MARK_PRICE),
                    "funding_rate": redis_cache.get(CacheKeys.LATEST_FUNDING_RATE),
                    "open_interest": redis_cache.get(CacheKeys.CURRENT_OPEN_INTEREST),
                    "daily_outlook": redis_cache.get(CacheKeys.LATEST_DAILY_OUTLOOK),
                    "trading_plan": redis_cache.get(CacheKeys.ACTIVE_TRADING_PLAN),
                    "market_intelligence": redis_cache.get(CacheKeys.LATEST_MARKET_INTELLIGENCE),
                },
            },
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.clients.discard(websocket)
        log.info("WS client disconnected (n={})", len(self.clients))

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception:  # noqa: BLE001
            await self.disconnect(websocket)

    async def broadcast(self, event_type: str, data: Any) -> None:
        message = {"type": event_type, "timestamp": _utc(), "data": data}
        redis_cache.set(CacheKeys.WS_BROADCAST, message, ttl_sec=60)
        async with self._lock:
            clients = list(self.clients)
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    async def publish_price(self, symbol: str, price: float) -> None:
        redis_cache.set(CacheKeys.LATEST_MARK_PRICE, price)
        await self.broadcast("price", {"symbol": symbol, "price": price})

    async def publish_alert(self, alert: dict[str, Any]) -> None:
        await self.broadcast("alert", alert)

    async def publish_dashboard(self, payload: dict[str, Any]) -> None:
        await self.broadcast("dashboard", payload)


hub = WebSocketHub()


async def websocket_endpoint(websocket: WebSocket) -> None:
    await hub.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            # Clients may ping; echo ack
            if raw.strip().lower() in {"ping", '{"type":"ping"}'}:
                await hub.send_personal(websocket, {"type": "pong", "timestamp": _utc()})
    except WebSocketDisconnect:
        await hub.disconnect(websocket)
    except Exception as exc:  # noqa: BLE001
        log.warning("WS error: {}", exc)
        await hub.disconnect(websocket)
