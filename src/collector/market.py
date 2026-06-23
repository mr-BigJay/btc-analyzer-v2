import logging

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.collector.base import BaseCollector
from src.collector.exchange import get_exchange_provider
from src.config import settings
from src.db.models import (
    FundingRate,
    LongShortRatio,
    OHLCVCandle,
    OpenInterest,
    TakerVolume,
    TickerSnapshot,
)

logger = logging.getLogger(__name__)


class MarketDataCollector(BaseCollector):
    source_name = "market_data"

    def __init__(self) -> None:
        super().__init__()
        self.exchange = get_exchange_provider()

    def collect_klines(self, session: Session, timeframe: str) -> int:
        rows_raw = self.exchange.fetch_klines(timeframe, settings.klines_limit)
        now = self.now()
        rows = [
            {
                "symbol": settings.symbol,
                "timeframe": timeframe,
                **row,
                "collected_at": now,
            }
            for row in rows_raw
        ]

        if not rows:
            return 0

        stmt = sqlite_insert(OHLCVCandle).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timeframe", "open_time"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "quote_volume": stmt.excluded.quote_volume,
                "trades": stmt.excluded.trades,
                "collected_at": stmt.excluded.collected_at,
            },
        )
        session.execute(stmt)
        session.commit()
        logger.info(
            "Collected %d %s candles via %s",
            len(rows),
            timeframe,
            self.exchange.name,
        )
        return len(rows)

    def collect_all_timeframes(self, session: Session) -> int:
        return sum(self.collect_klines(session, tf) for tf in settings.timeframes)

    def collect_ticker(self, session: Session) -> int:
        data = self.exchange.fetch_ticker()
        now = self.now()
        snapshot = TickerSnapshot(
            symbol=settings.symbol,
            timestamp=now,
            **data,
        )
        session.add(snapshot)
        session.commit()
        logger.info("Ticker via %s: $%s", self.exchange.name, snapshot.price)
        return 1

    def collect_funding_rate(self, session: Session) -> int:
        rows_raw = self.exchange.fetch_funding_rates(100)
        now = self.now()
        rows = [
            {
                "symbol": settings.futures_symbol,
                **row,
                "collected_at": now,
            }
            for row in rows_raw
        ]
        if not rows:
            return 0

        stmt = sqlite_insert(FundingRate).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "funding_time"],
            set_={
                "funding_rate": stmt.excluded.funding_rate,
                "mark_price": stmt.excluded.mark_price,
                "collected_at": stmt.excluded.collected_at,
            },
        )
        session.execute(stmt)
        session.commit()
        return len(rows)

    def collect_open_interest(self, session: Session) -> int:
        rows_raw = self.exchange.fetch_open_interest_history(168)
        now = self.now()
        rows = [
            {
                "symbol": settings.futures_symbol,
                **row,
                "collected_at": now,
            }
            for row in rows_raw
        ]
        if not rows:
            return 0

        stmt = sqlite_insert(OpenInterest).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timestamp"],
            set_={
                "open_interest": stmt.excluded.open_interest,
                "open_interest_value": stmt.excluded.open_interest_value,
                "collected_at": stmt.excluded.collected_at,
            },
        )
        session.execute(stmt)
        session.commit()
        return len(rows)

    def collect_long_short_ratio(self, session: Session) -> int:
        rows_raw = self.exchange.fetch_long_short_ratios(168)
        now = self.now()
        rows = [
            {
                "symbol": settings.futures_symbol,
                **row,
                "collected_at": now,
            }
            for row in rows_raw
        ]
        if not rows:
            return 0

        stmt = sqlite_insert(LongShortRatio).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "ratio_type", "timestamp"],
            set_={
                "long_account": stmt.excluded.long_account,
                "short_account": stmt.excluded.short_account,
                "long_short_ratio": stmt.excluded.long_short_ratio,
                "collected_at": stmt.excluded.collected_at,
            },
        )
        session.execute(stmt)
        session.commit()
        return len(rows)

    def collect_taker_volume(self, session: Session) -> int:
        rows_raw = self.exchange.fetch_taker_volumes(168)
        now = self.now()
        rows = [
            {
                "symbol": settings.futures_symbol,
                **row,
                "collected_at": now,
            }
            for row in rows_raw
        ]
        if not rows:
            return 0

        stmt = sqlite_insert(TakerVolume).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "timestamp"],
            set_={
                "buy_volume": stmt.excluded.buy_volume,
                "sell_volume": stmt.excluded.sell_volume,
                "buy_sell_ratio": stmt.excluded.buy_sell_ratio,
                "collected_at": stmt.excluded.collected_at,
            },
        )
        session.execute(stmt)
        session.commit()
        return len(rows)

    def collect_derivatives(self, session: Session) -> int:
        return (
            self.collect_funding_rate(session)
            + self.collect_open_interest(session)
            + self.collect_long_short_ratio(session)
            + self.collect_taker_volume(session)
        )
