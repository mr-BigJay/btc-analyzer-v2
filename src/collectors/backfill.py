"""Historical backfill — isolated from live streams (Ch.12 §12.17)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.config import settings
from src.storage.repository import CentralRepository

logger = logging.getLogger(__name__)


@dataclass
class BackfillResult:
    ok: bool
    symbol: str
    timeframe: str
    candles_fetched: int = 0
    candles_stored: int = 0
    gaps_repaired: int = 0
    warnings: list[str] = field(default_factory=list)
    completed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "candles_fetched": self.candles_fetched,
            "candles_stored": self.candles_stored,
            "gaps_repaired": self.gaps_repaired,
            "warnings": self.warnings,
            "completed_at": self.completed_at,
        }


class HistoricalBackfill:
    """Bootstrap / gap repair / scheduled archival refresh — not mixed with live WS."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()

    def backfill_ohlcv(
        self,
        *,
        symbol: str | None = None,
        timeframe: str = "1h",
        limit: int = 500,
    ) -> BackfillResult:
        import asyncio

        from src.collectors.binance import BinanceFuturesCollector

        symbol = symbol or settings.binance_symbol
        warnings: list[str] = []
        collector = BinanceFuturesCollector(self.repository)

        async def _fetch() -> list[dict]:
            return await collector.collect_ohlcv_async(interval=timeframe, limit=limit)

        try:
            ohlcv = asyncio.run(_fetch())
        except Exception as exc:  # noqa: BLE001
            logger.warning("backfill fetch failed: %s", exc)
            return BackfillResult(ok=False, symbol=symbol, timeframe=timeframe, warnings=[str(exc)])

        if not isinstance(ohlcv, list):
            return BackfillResult(ok=False, symbol=symbol, timeframe=timeframe, warnings=["empty ohlcv"])

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "timeframe": timeframe,
            "exchange": "binance",
            "ohlcv": ohlcv,
            "source_id": f"backfill-{timeframe}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "backfill": True,
        }
        try:
            self.repository.append_technical_cache(record)
            stored = len(ohlcv)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"persist failed: {exc}")
            stored = 0

        return BackfillResult(
            ok=stored > 0,
            symbol=symbol,
            timeframe=timeframe,
            candles_fetched=len(ohlcv),
            candles_stored=stored,
            gaps_repaired=0,
            warnings=warnings,
        )
