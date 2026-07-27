"""Retention policy enforcement (Ch.4 §4.9 / Ch.11 §11.21).

Analytical intelligence and reports are permanent. Tick/trade noise expires.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.db.models import ApiCallLog, ErrorLog, MarketCandle, OrderBookSnapshot, SchedulerLog, Trade
from src.db.session import get_session

logger = logging.getLogger(__name__)

# Days retained (None / missing = permanent)
RETENTION_DAYS = {
    "trades": 90,  # tick / trade noise — short-medium
    "orderbook_snapshot": 30,
    "tick_candles": 14,  # timeframe == "tick"
    "api_call_logs": 30,
    "error_logs": 90,
    "scheduler_logs": 60,
    # Permanent: market_candles (1m+), funding, OI, options, technical,
    # structure, scores, ai_decisions, reports, liquidity, volatility
}


def apply_retention(*, now: datetime | None = None) -> dict[str, int]:
    """Delete expired rows per retention policy. Returns deleted counts."""
    now = now or datetime.now(timezone.utc)
    deleted: dict[str, int] = {}
    session = get_session()
    try:
        trade_cutoff = now - timedelta(days=RETENTION_DAYS["trades"])
        deleted["trades"] = (
            session.query(Trade).filter(Trade.timestamp < trade_cutoff).delete(synchronize_session=False)
        )

        ob_cutoff = now - timedelta(days=RETENTION_DAYS["orderbook_snapshot"])
        deleted["orderbook_snapshot"] = (
            session.query(OrderBookSnapshot)
            .filter(OrderBookSnapshot.timestamp < ob_cutoff)
            .delete(synchronize_session=False)
        )

        tick_cutoff = now - timedelta(days=RETENTION_DAYS["tick_candles"])
        deleted["tick_candles"] = (
            session.query(MarketCandle)
            .filter(MarketCandle.timeframe == "tick", MarketCandle.timestamp < tick_cutoff)
            .delete(synchronize_session=False)
        )

        api_cutoff = now - timedelta(days=RETENTION_DAYS["api_call_logs"])
        deleted["api_call_logs"] = (
            session.query(ApiCallLog).filter(ApiCallLog.timestamp < api_cutoff).delete(synchronize_session=False)
        )

        err_cutoff = now - timedelta(days=RETENTION_DAYS["error_logs"])
        deleted["error_logs"] = (
            session.query(ErrorLog).filter(ErrorLog.timestamp < err_cutoff).delete(synchronize_session=False)
        )

        sched_cutoff = now - timedelta(days=RETENTION_DAYS["scheduler_logs"])
        deleted["scheduler_logs"] = (
            session.query(SchedulerLog)
            .filter(SchedulerLog.timestamp < sched_cutoff)
            .delete(synchronize_session=False)
        )

        session.commit()
        logger.info("Retention applied: %s", deleted)
        return deleted
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
