"""Binance WebSocket stream subscriptions (Ch.3 §3.6)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from src.collectors.websocket import WebSocketClient

MessageHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class BinanceWebSocket:
    """Subscribe to futures combined streams."""

    WS_BASE = "wss://fstream.binance.com/stream"

    STREAMS = (
        "trade",
        "aggTrade",
        "depth",
        "bookTicker",
        "forceOrder",  # liquidations
        "markPrice",
    )

    def __init__(self, symbol: str = "btcusdt", on_message: MessageHandler | None = None) -> None:
        sym = symbol.lower()
        streams = "/".join(
            [
                f"{sym}@trade",
                f"{sym}@aggTrade",
                f"{sym}@depth5@100ms",
                f"{sym}@bookTicker",
                f"{sym}@forceOrder",
                f"{sym}@markPrice@1s",
            ]
        )
        url = f"{self.WS_BASE}?streams={streams}"
        self.client = WebSocketClient("binance", url, on_message=on_message)

    def start(self):
        return self.client.start()

    async def stop(self) -> None:
        await self.client.stop()
