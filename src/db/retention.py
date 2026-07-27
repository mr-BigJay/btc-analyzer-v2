"""Retention policy enforcement (Ch.4 §4.9)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.db.models import OrderBookSnapshot, Trade
from src.db.session import get_session

logger = logging.getLogger(__name__)

RETENTION_DAYS = {
    "trades": 90,
    "orderbook_snapshot": 30,
    # Permanent: market_candles, funding_rates, options_*, daily_outlook, trading_plan
}


def apply_retention(*, now: datetime | None = None) -> dict[str, int]:
    """Delete expired rows per retention policy. Returns deleted counts."""
    now = now or datetime.now(timezone.utc)
    deleted: dict[str, int] = {}
    session = get_session()
    try:
        trade_cutoff = now - timedelta(days=RETENTION_DAYS["trades"])
        q = session.query(Trade).filter(Trade.timestamp < trade_cutoff)
        deleted["trades"] = q.delete(synchronize_session=False)

        ob_cutoff = now - timedelta(days=RETENTION_DAYS["orderbook_snapshot"])
        q2 = session.query(OrderBookSnapshot).filter(OrderBookSnapshot.timestamp < ob_cutoff)
        deleted["orderbook_snapshot"] = q2.delete(synchronize_session=False)

        session.commit()
        logger.info("Retention applied: %s", deleted)
        return deleted
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
