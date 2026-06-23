"""Macro data collector — SPX, NDX, DXY via Yahoo Finance."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.collector.base import BaseCollector
from src.config import settings
from src.db.models import MacroMetric

logger = logging.getLogger(__name__)

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BTCAnalyzer/1.0)"}


class MacroCollector(BaseCollector):
    source_name = "yahoo_macro"

    def _fetch_symbol(self, yahoo_symbol: str) -> dict:
        with httpx.Client(timeout=self.timeout, headers=HEADERS) as client:
            resp = client.get(
                YAHOO_CHART.format(symbol=yahoo_symbol),
                params={"interval": "1d", "range": "1mo"},
            )
            resp.raise_for_status()
            result = resp.json()["chart"]["result"][0]
            meta = result["meta"]
            closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
            price = float(meta["regularMarketPrice"])
            change_1d = 0.0
            if len(closes) >= 2 and closes[-2]:
                change_1d = (price / closes[-2] - 1) * 100
            change_7d = 0.0
            if len(closes) >= 6 and closes[-6]:
                change_7d = (price / closes[-6] - 1) * 100
            ts = datetime.fromtimestamp(meta["regularMarketTime"], tz=timezone.utc)
            return {
                "price": price,
                "change_1d_pct": round(change_1d, 2),
                "change_7d_pct": round(change_7d, 2),
                "timestamp": ts,
            }

    def collect(self, session: Session) -> int:
        now = self.now()
        rows = []
        for name, yahoo_sym in settings.macro_symbols.items():
            try:
                data = self._fetch_symbol(yahoo_sym)
                rows.append(
                    {
                        "symbol": name,
                        "price": data["price"],
                        "change_1d_pct": data["change_1d_pct"],
                        "change_7d_pct": data["change_7d_pct"],
                        "timestamp": data["timestamp"],
                        "collected_at": now,
                    }
                )
                logger.info(
                    "Macro %s: %.2f (1d: %+.2f%%, 7d: %+.2f%%)",
                    name.upper(),
                    data["price"],
                    data["change_1d_pct"],
                    data["change_7d_pct"],
                )
            except Exception:
                logger.exception("Failed to collect macro %s", name)

        if not rows:
            return 0

        stmt = sqlite_insert(MacroMetric).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timestamp"],
            set_={
                "price": stmt.excluded.price,
                "change_1d_pct": stmt.excluded.change_1d_pct,
                "change_7d_pct": stmt.excluded.change_7d_pct,
                "collected_at": stmt.excluded.collected_at,
            },
        )
        session.execute(stmt)
        session.commit()
        return len(rows)
