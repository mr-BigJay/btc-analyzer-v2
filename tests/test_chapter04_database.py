"""Chapter 4 database schema + integrity tests."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Isolate test DB before importing app modules that bind the engine
TEST_DB = Path("/tmp/btc_analyzer_ch4_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""

from src.config import settings  # noqa: E402
from src.db.models import (  # noqa: E402
    Exchange,
    FundingRate,
    OrderBookSnapshot,
    Symbol,
    Trade,
)
from src.db.retention import apply_retention  # noqa: E402
from src.db.session import get_session, init_db, reset_engine  # noqa: E402
from src.storage.repository import CentralRepository  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    reset_engine()
    if TEST_DB.exists():
        TEST_DB.unlink()
    # settings already read DATABASE_URL from env at import — force
    settings.database_url = f"sqlite:///{TEST_DB}"
    init_db(seed=True)
    yield
    reset_engine()


def test_seed_exchanges_and_symbols():
    session = get_session()
    try:
        names = {e.name for e in session.query(Exchange).all()}
        assert {"binance", "deribit", "coinex", "bitunix"} <= names
        sym = session.query(Symbol).filter_by(symbol="BTCUSDT").one()
        assert sym.base_asset == "BTC"
    finally:
        session.close()


def test_funding_requires_fk_and_repository_writes():
    repo = CentralRepository()
    repo.append_futures(
        {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "funding_rate": 0.0001,
            "open_interest": 12345.0,
            "open_interest_value": 8.5e8,
        }
    )
    session = get_session()
    try:
        rows = session.query(FundingRate).all()
        assert len(rows) == 1
        assert rows[0].exchange_id is not None
        assert rows[0].symbol_id is not None
    finally:
        session.close()


def test_orderbook_and_retention():
    repo = CentralRepository()
    old_ts = datetime.now(timezone.utc) - timedelta(days=45)
    session = get_session()
    try:
        ex = session.query(Exchange).filter_by(name="binance").one()
        sym = session.query(Symbol).filter_by(symbol="BTCUSDT").one()
        session.add(
            OrderBookSnapshot(
                exchange_id=ex.id,
                symbol_id=sym.id,
                timestamp=old_ts,
                best_bid=1.0,
                best_ask=1.1,
                spread=0.1,
            )
        )
        session.add(
            Trade(
                exchange_id=ex.id,
                symbol_id=sym.id,
                timestamp=datetime.now(timezone.utc) - timedelta(days=120),
                price=100.0,
                quantity=1.0,
                side="BUY",
            )
        )
        session.commit()
    finally:
        session.close()

    deleted = apply_retention()
    assert deleted["orderbook_snapshot"] >= 1
    assert deleted["trades"] >= 1


def test_coinex_analysis_append():
    repo = CentralRepository()
    repo.append_coinex_analysis(
        {
            "symbol": "BTCUSDT",
            "summary": "Test title",
            "raw_article": "# hello",
            "bullish_arguments": ["up"],
            "bearish_arguments": ["down"],
            "support_levels": [64000],
            "resistance_levels": [66000],
            "confidence_score": 0.7,
            "bias": "neutral",
            "publication_time": datetime.now(timezone.utc).isoformat(),
        }
    )
