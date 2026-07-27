"""WebSocket client scaffold (Ch.3 §3.5 / §3.6 streams).

Real-time streams: trades, depth, liquidations, mark price.
Collectors own their WS lifecycle — no cross-collector sharing.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class WebSocketClient:
    """Minimal HTTPS-upgrade WebSocket client with reconnect backoff."""

    def __init__(
        self,
        exchange: str,
        url: str,
        *,
        on_message: MessageHandler | None = None,
        reconnect_delays: tuple[float, ...] = (5.0, 15.0, 30.0),
    ) -> None:
        if not url.startswith("wss://"):
            raise ValueError(f"{exchange} WebSocket requires wss:// (Ch.3 §3.18)")
        self.exchange = exchange
        self.url = url
        self.on_message = on_message
        self.reconnect_delays = reconnect_delays
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def _run_loop(self) -> None:
        try:
            import aiohttp
        except ImportError as exc:
            raise RuntimeError("aiohttp required for WebSocket collectors") from exc

        attempt = 0
        while not self._stop.is_set():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.url, heartbeat=20) as ws:
                        logger.info("%s WS connected %s", self.exchange, self.url)
                        attempt = 0
                        async for msg in ws:
                            if self._stop.is_set():
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    payload = json.loads(msg.data)
                                except json.JSONDecodeError:
                                    continue
                                if self.on_message:
                                    result = self.on_message(payload)
                                    if asyncio.iscoroutine(result):
                                        await result
                            elif msg.type in (
                                aiohttp.WSMsgType.CLOSED,
                                aiohttp.WSMsgType.ERROR,
                            ):
                                break
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s WS error: %s", self.exchange, exc)

            if self._stop.is_set():
                break
            delay = self.reconnect_delays[min(attempt, len(self.reconnect_delays) - 1)]
            attempt += 1
            logger.info("%s WS reconnect in %.0fs", self.exchange, delay)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

    def start(self) -> asyncio.Task:
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop(), name=f"ws-{self.exchange}")
        return self._task

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await asyncio.wait([self._task], timeout=5.0)
            self._task = None
