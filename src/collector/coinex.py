"""CoinEx USDT-M futures market data (public API)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.collector.base import BaseCollector
from src.config import settings
from src.db.models import CoinExFuturesSnapshot

logger = logging.getLogger(__name__)


class CoinExFuturesCollector(BaseCollector):
    source_name = "coinex_futures"

    def _coinex_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        data = self._get(f"{settings.coinex_api_base}{path}", params)
        if data.get("code") != 0:
            raise RuntimeError(f"CoinEx API error: {data.get('message', data)}")
        return data.get("data", [])

    def fetch_ticker(self, market: str) -> dict[str, Any]:
        rows = self._coinex_get("/futures/ticker", {"market": market})
        if not rows:
            raise RuntimeError(f"CoinEx ticker empty for {market}")
        return rows[0]

    def fetch_funding(self, market: str) -> dict[str, Any]:
        rows = self._coinex_get("/futures/funding-rate", {"market": market})
        if not rows:
            raise RuntimeError(f"CoinEx funding empty for {market}")
        return rows[0]

    def collect(self, session: Session) -> int:
        market = settings.coinex_market
        ticker = self.fetch_ticker(market)
        funding = self.fetch_funding(market)

        last = float(ticker["last"])
        mark = float(ticker.get("mark_price") or last)
        index = float(ticker.get("index_price") or last)
        premium_pct = ((mark - index) / index * 100) if index else 0.0

        buy_vol = float(ticker.get("volume_buy") or 0)
        sell_vol = float(ticker.get("volume_sell") or 0)
        taker_ratio = buy_vol / sell_vol if sell_vol else 0.0

        funding_rate = float(funding.get("latest_funding_rate") or 0)
        next_funding_rate = float(funding.get("next_funding_rate") or funding_rate)
        open_interest = float(ticker.get("open_interest_volume") or 0)

        prev = session.execute(
            select(CoinExFuturesSnapshot)
            .where(CoinExFuturesSnapshot.market == market)
            .order_by(CoinExFuturesSnapshot.collected_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        oi_change_pct = None
        if prev and prev.open_interest and open_interest:
            oi_change_pct = round((open_interest - prev.open_interest) / prev.open_interest * 100, 2)

        now = self.now()
        row = CoinExFuturesSnapshot(
            market=market,
            last_price=last,
            mark_price=mark,
            index_price=index,
            premium_pct=round(premium_pct, 4),
            funding_rate=funding_rate,
            next_funding_rate=next_funding_rate,
            open_interest=open_interest,
            oi_change_pct=oi_change_pct,
            volume_24h=float(ticker.get("volume") or 0),
            volume_buy=buy_vol,
            volume_sell=sell_vol,
            taker_buy_sell_ratio=round(taker_ratio, 4),
            collected_at=now,
        )
        session.add(row)
        session.commit()

        logger.info(
            "CoinEx %s: last=$%s funding=%.5f OI=%.2f premium=%.3f%% taker=%.2f",
            market,
            last,
            funding_rate,
            open_interest,
            premium_pct,
            taker_ratio,
        )
        return 1
