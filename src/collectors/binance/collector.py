"""Binance Futures collector — primary market reference (Ch.3 §3.6).

No analysis. No communication with other collectors.
"""

from __future__ import annotations

import asyncio
import logging

from src.collectors.base import BaseCollector
from src.collectors.binance.auth import BinanceAuth
from src.collectors.binance.parser import parse_futures_bundle, parse_ohlcv, parse_spot_ticker
from src.collectors.binance.rest import BinanceRestClient
from src.collectors.binance.websocket import BinanceWebSocket
from src.config import settings
from src.core import FlowObject, ModuleResult, ModuleStatus
from src.storage.repository import CentralRepository

logger = logging.getLogger(__name__)


class BinanceFuturesCollector(BaseCollector[FlowObject]):
    MODULE = "Binance"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        super().__init__(repository)
        self.auth = BinanceAuth()
        self.rest = BinanceRestClient(self.auth)
        self.symbol = settings.binance_symbol
        self._ws: BinanceWebSocket | None = None

    def _rebuild_data(self, raw: dict) -> FlowObject:
        fields = FlowObject.__dataclass_fields__
        return FlowObject(**{k: v for k, v in raw.items() if k in fields})

    async def collect_async(self) -> ModuleResult[FlowObject]:
        results = await asyncio.gather(
            self.rest.mark_premium(self.symbol),
            self.rest.open_interest(self.symbol),
            self.rest.funding_history(self.symbol),
            self.rest.long_short_ratio(self.symbol),
            self.rest.depth(self.symbol),
            self.rest.open_interest_hist(self.symbol),
            self.rest.ticker_price(self.symbol),
            return_exceptions=True,
        )
        labels = (
            "premium",
            "oi",
            "funding",
            "ls",
            "depth",
            "oi_hist",
            "ticker",
        )
        errors = []
        values: dict = {}
        for label, value in zip(labels, results):
            if isinstance(value, Exception):
                errors.append(f"{label}:{value}")
                values[label] = {} if label not in {"funding", "ls", "oi_hist"} else []
            else:
                values[label] = value

        # Critical path: need at least mark/premium or ticker
        if isinstance(results[0], Exception) and isinstance(results[6], Exception):
            raise RuntimeError("; ".join(errors[:3]) or "Binance critical endpoints failed")

        raw = parse_futures_bundle(
            self.symbol,
            premium=values["premium"] if isinstance(values["premium"], dict) else {},
            oi=values["oi"] if isinstance(values["oi"], dict) else {},
            funding_hist=values["funding"] if isinstance(values["funding"], list) else [],
            ls_ratio=values["ls"] if isinstance(values["ls"], list) else [],
            depth=values["depth"] if isinstance(values["depth"], dict) else {},
            oi_hist=values["oi_hist"] if isinstance(values["oi_hist"], list) else [],
            ticker=values["ticker"] if isinstance(values["ticker"], dict) else {},
        )
        flow = FlowObject(
            symbol=self.symbol,
            mark_price=raw.get("mark_price"),
            index_price=raw.get("index_price"),
            funding_rate=raw.get("funding_rate"),
            funding_history=raw.get("funding_history") or [],
            open_interest=raw.get("open_interest"),
            open_interest_value=raw.get("open_interest_value"),
            long_short_ratio=raw.get("long_short_ratio"),
            premium_index=raw.get("premium_index"),
            basis=raw.get("basis"),
            liquidations=raw.get("liquidations") or {},
            order_book=raw.get("order_book") or {},
            volume=raw.get("volume"),
        )
        confidence = 1.0 if not errors else max(0.3, 1.0 - 0.1 * len(errors))
        return ModuleResult(
            module=self.MODULE,
            status=ModuleStatus.OK if flow.mark_price or flow.funding_rate or raw.get("price") else ModuleStatus.DEGRADED,
            confidence=confidence,
            data=flow,
            source_live=True,
            warning="; ".join(errors[:5]) if errors else None,
        )

    def collect(self) -> ModuleResult[FlowObject]:
        return asyncio.run(self.collect_async())

    async def collect_spot_async(self) -> dict:
        ticker = await self.rest.spot_ticker(self.symbol)
        return parse_spot_ticker(self.symbol, ticker)

    async def collect_ohlcv_async(self, interval: str = "1h", limit: int = 100) -> list[dict]:
        klines = await self.rest.klines(self.symbol, interval=interval, limit=limit)
        return parse_ohlcv(klines)

    def start_websocket(self, on_message=None) -> None:
        self._ws = BinanceWebSocket(symbol=self.symbol.lower(), on_message=on_message)
        self._ws.start()

    async def stop_websocket(self) -> None:
        if self._ws:
            await self._ws.stop()
            self._ws = None
