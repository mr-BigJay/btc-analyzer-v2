"""Liquidation data collector from OKX."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.collector.base import BaseCollector
from src.config import settings
from src.db.models import LiquidationEvent, LiquidationLevel

logger = logging.getLogger(__name__)

OKX_LIQ_URL = "https://www.okx.com/api/v5/public/liquidation-orders"


class LiquidationCollector(BaseCollector):
    source_name = "okx_liquidations"

    def _fetch_orders(self, limit: int = 100) -> list[dict]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                OKX_LIQ_URL,
                params={
                    "instType": "SWAP",
                    "uly": settings.okx_inst_id,
                    "state": "filled",
                    "limit": str(limit),
                },
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("code") != "0":
            raise RuntimeError(f"OKX liquidation error: {data.get('msg')}")
        orders = []
        for batch in data.get("data", []):
            orders.extend(batch.get("details", []))
        return orders

    def collect(self, session: Session) -> int:
        orders = self._fetch_orders(limit=100)
        now = self.now()
        rows = []
        spot_estimate = 63000.0

        for o in orders:
            price = float(o["bkPx"])
            size = float(o["sz"])
            side = o.get("side", "")
            pos_side = o.get("posSide", "")
            ts = self.ms_to_datetime(int(o.get("ts", o.get("time", 0))))
            value_usd = price * size
            rows.append(
                {
                    "symbol": settings.symbol,
                    "price": price,
                    "size": size,
                    "side": side,
                    "pos_side": pos_side,
                    "value_usd": value_usd,
                    "timestamp": ts,
                    "collected_at": now,
                }
            )
            spot_estimate = price

        if not rows:
            return 0

        session.execute(sqlite_insert(LiquidationEvent).values(rows))
        self._aggregate_levels(session, rows, spot_estimate, now)
        session.commit()
        logger.info("Collected %d liquidation events", len(rows))
        return len(rows)

    def _aggregate_levels(
        self, session: Session, rows: list[dict], spot: float, now: datetime
    ) -> None:
        bin_size = spot * settings.liquidation_bin_pct / 100
        if bin_size <= 0:
            bin_size = 500

        bins: dict[float, dict[str, float]] = {}
        for r in rows:
            level = round(round(r["price"] / bin_size) * bin_size, 2)
            if level not in bins:
                bins[level] = {"long": 0.0, "short": 0.0}
            if r["pos_side"] == "long":
                bins[level]["long"] += r["value_usd"]
            else:
                bins[level]["short"] += r["value_usd"]

        level_rows = [
            {
                "symbol": settings.symbol,
                "price_level": lvl,
                "long_liq_usd": v["long"],
                "short_liq_usd": v["short"],
                "total_usd": v["long"] + v["short"],
                "snapshot_at": now,
            }
            for lvl, v in bins.items()
        ]
        if level_rows:
            session.execute(sqlite_insert(LiquidationLevel).values(level_rows))
