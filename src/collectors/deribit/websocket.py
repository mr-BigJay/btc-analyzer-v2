"""Deribit WebSocket — public ticker / book streams."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from src.collectors.websocket import WebSocketClient

MessageHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class DeribitWebSocket:
    WS_URL = "wss://www.deribit.com/ws/api/v2"

    def __init__(self, on_message: MessageHandler | None = None) -> None:
        self.client = WebSocketClient("deribit", self.WS_URL, on_message=on_message)

    def start(self):
        return self.client.start()

    async def stop(self) -> None:
        await self.client.stop()
