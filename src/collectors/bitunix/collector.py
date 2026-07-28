"""Bitunix collector — execution validation market data (Ch.3 §3.9).

Bitunix is never the primary analytical source (Binance is).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from src.collectors.base import BaseCollector
from src.collectors.bitunix.auth import BitunixAuth
from src.collectors.bitunix.parser import parse_validation_snapshot
from src.collectors.bitunix.rest import BitunixRestClient
from src.config import settings
from src.core import ModuleResult, ModuleStatus, utc_now_iso
from src.storage.repository import CentralRepository

logger = logging.getLogger(__name__)


@dataclass
class BitunixSnapshot:
    """Execution-validation market snapshot (not FlowObject / analysis)."""

    symbol: str = "BTCUSDT"
    price: float | None = None
    funding_rate: float | None = None
    order_book: dict = field(default_factory=dict)
    spread: float | None = None
    open_interest: float | None = None
    volume: float | None = None
    collected_at: str = field(default_factory=utc_now_iso)


class BitunixCollector(BaseCollector[BitunixSnapshot]):
    MODULE = "Bitunix"
    MARKET = "Futures"

    def __init__(self, repository: CentralRepository | None = None) -> None:
        super().__init__(repository)
        self.auth = BitunixAuth()
        self.rest = BitunixRestClient(self.auth)
        self.symbol = settings.binance_symbol

    def _rebuild_data(self, raw: dict) -> BitunixSnapshot:
        fields = BitunixSnapshot.__dataclass_fields__
        return BitunixSnapshot(**{k: v for k, v in raw.items() if k in fields})

    async def collect_async(self) -> ModuleResult[BitunixSnapshot]:
        if not settings.bitunix_enabled:
            return ModuleResult(
                module=self.MODULE,
                status=ModuleStatus.SKIPPED,
                confidence=0.0,
                data=BitunixSnapshot(symbol=self.symbol),
                warning="Bitunix disabled",
                source_live=False,
            )

        ticker, depth, funding = await asyncio.gather(
            self.rest.ticker(self.symbol),
            self.rest.depth(self.symbol),
            self.rest.funding(self.symbol),
            return_exceptions=True,
        )
        if isinstance(ticker, Exception):
            raise RuntimeError(f"Bitunix ticker failed: {ticker}") from ticker
        depth_data = depth if not isinstance(depth, Exception) else {}
        funding_data = funding if not isinstance(funding, Exception) else {}

        raw = parse_validation_snapshot(self.symbol, ticker, depth_data, funding_data)
        snap = BitunixSnapshot(
            symbol=self.symbol,
            price=raw.get("price"),
            funding_rate=raw.get("funding_rate"),
            order_book=raw.get("order_book") or {},
            spread=raw.get("spread"),
            open_interest=raw.get("open_interest"),
            volume=raw.get("volume"),
        )
        return ModuleResult(
            module=self.MODULE,
            status=ModuleStatus.OK,
            confidence=0.8 if snap.price else 0.3,
            data=snap,
            source_live=True,
        )

    def collect(self) -> ModuleResult[BitunixSnapshot]:
        return asyncio.run(self.collect_async())

    def collect_raw_dict(self) -> dict[str, Any]:
        result = self.collect_resilient()
        return result.to_dict()
