"""Seed reference exchanges / symbols / settings (Ch.4 §4.5, §4.13)."""

from __future__ import annotations

import logging

from src.db.models import Exchange, Symbol, SystemSetting
from src.db.session import get_session

logger = logging.getLogger(__name__)

DEFAULT_EXCHANGES = [
    {"name": "binance", "type": "futures", "priority": "critical", "status": "active"},
    {"name": "deribit", "type": "options", "priority": "critical", "status": "active"},
    {"name": "coinex", "type": "narrative", "priority": "high", "status": "active"},
    {"name": "bitunix", "type": "futures", "priority": "medium", "status": "active"},
]

DEFAULT_SYMBOLS = [
    {"symbol": "BTCUSDT", "base_asset": "BTC", "quote_asset": "USDT", "status": "active"},
]

DEFAULT_SETTINGS = [
    {"key": "default_symbol", "value": "BTCUSDT", "domain": "trading"},
    {"key": "default_timeframes", "value": "1m,5m,15m,1h,4h,1d", "domain": "trading"},
    {"key": "timezone", "value": "UTC", "domain": "system"},
    {"key": "retention_trades_days", "value": "90", "domain": "retention"},
    {"key": "retention_orderbook_days", "value": "30", "domain": "retention"},
]


def seed_reference_data() -> None:
    session = get_session()
    try:
        for row in DEFAULT_EXCHANGES:
            existing = session.query(Exchange).filter_by(name=row["name"]).one_or_none()
            if existing is None:
                session.add(Exchange(**row))
            else:
                existing.type = row["type"]
                existing.priority = row["priority"]
                existing.status = row["status"]

        for row in DEFAULT_SYMBOLS:
            existing = session.query(Symbol).filter_by(symbol=row["symbol"]).one_or_none()
            if existing is None:
                session.add(Symbol(**row))

        for row in DEFAULT_SETTINGS:
            existing = session.query(SystemSetting).filter_by(key=row["key"]).one_or_none()
            if existing is None:
                session.add(SystemSetting(**row))
            else:
                existing.value = row["value"]
                existing.domain = row["domain"]

        session.commit()
        logger.info("Reference data seeded (exchanges/symbols/settings)")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def resolve_exchange_id(session, name: str) -> int:
    name = name.lower()
    row = session.query(Exchange).filter_by(name=name).one_or_none()
    if row is None:
        row = Exchange(name=name, type="futures", priority="medium", status="active")
        session.add(row)
        session.flush()
    return int(row.id)


def resolve_symbol_id(session, symbol: str) -> int:
    symbol = symbol.upper().replace("-", "").replace("_", "")
    row = session.query(Symbol).filter_by(symbol=symbol).one_or_none()
    if row is None:
        base, quote = "BTC", "USDT"
        if symbol.endswith("USDT"):
            base, quote = symbol[:-4], "USDT"
        elif symbol.endswith("USD"):
            base, quote = symbol[:-3], "USD"
        row = Symbol(symbol=symbol, base_asset=base, quote_asset=quote, status="active")
        session.add(row)
        session.flush()
    return int(row.id)
