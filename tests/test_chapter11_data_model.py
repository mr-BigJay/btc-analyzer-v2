"""Chapter 11 — Data Model & Database Architecture tests."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

TEST_DB = Path("/tmp/btc_analyzer_ch11_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""

from src.config import settings  # noqa: E402
from src.db.access import assert_can_write, can_write  # noqa: E402
from src.db.models import (  # noqa: E402
    AIDecisionRecord,
    AlertRecord,
    Exchange,
    FuturesData,
    MarketScore,
    ReportRecord,
    SpotData,
    Symbol,
)
from src.db.packages import build_data_package  # noqa: E402
from src.db.retention import apply_retention  # noqa: E402
from src.db.session import get_session, init_db, reset_engine  # noqa: E402
from src.storage.repository import CentralRepository  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    reset_engine()
    if TEST_DB.exists():
        TEST_DB.unlink()
    settings.database_url = f"sqlite:///{TEST_DB}"
    init_db(seed=True)
    yield
    reset_engine()


def test_asset_alias_and_exchange_metadata():
    session = get_session()
    try:
        sym = session.query(Symbol).filter_by(symbol="BTCUSDT").one()
        assert sym.public_id
        assert sym.base_asset == "BTC"
        ex = session.query(Exchange).filter_by(name="binance").one()
        assert ex.api_status == "unknown"
        assert hasattr(ex, "last_sync")
    finally:
        session.close()


def test_access_rules_deny_cross_module_write():
    assert can_write("scoring", "market_scores")
    assert not can_write("scoring", "reports")
    with pytest.raises(PermissionError):
        assert_can_write("ai", "market_scores")
    with pytest.raises(PermissionError):
        assert_can_write("collector", "ai_decisions")


def test_spot_and_futures_dual_write():
    repo = CentralRepository()
    ts = datetime.now(timezone.utc).isoformat()
    repo.append_spot(
        {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "timestamp": ts,
            "price": 65000.0,
            "volume": 12.5,
            "vwap": 64950.0,
            "cvd": 100.0,
        }
    )
    repo.append_futures(
        {
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "timestamp": ts,
            "funding_rate": 0.0001,
            "open_interest": 5000.0,
            "open_interest_value": 3.2e8,
            "long_ratio": 0.55,
            "short_ratio": 0.45,
        }
    )
    session = get_session()
    try:
        assert session.query(SpotData).count() == 1
        fut = session.query(FuturesData).one()
        assert fut.open_interest == 5000.0
        assert fut.funding_rate == 0.0001
    finally:
        session.close()


def test_scores_ai_reports_alerts_persist():
    repo = CentralRepository()
    repo.append_market_score(
        {
            "symbol": "BTCUSDT",
            "market_bias_score": 42.0,
            "confidence_score": 70.0,
            "risk_score": 35.0,
            "market_health_index": 62.0,
            "market_stress_index": 40.0,
            "data_quality_score": 88.0,
            "market_bias": "Bullish",
            "weight_regime": "trend",
        }
    )
    repo.append_ai_decision(
        {
            "symbol": "BTCUSDT",
            "market_bias": "Bullish",
            "primary_narrative": "Trend continuation",
            "confidence": 70.0,
            "scenarios": [{"name": "Bullish Continuation", "probability": 55}],
            "reasoning": {"primary_conclusion": "Bias bullish"},
            "risk_level": "Moderate",
            "analysis_fingerprint": "abc123",
        }
    )
    rid = str(uuid4())
    repo.append_report(
        {
            "report_type": "Daily Outlook",
            "published": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "report_id": rid,
                "symbol": "BTCUSDT",
                "engine_version": "3.0.0-dev",
                "ai_version": "7.0",
                "schema_version": "10.0",
            },
            "market_bias": "Bullish",
            "executive_summary": "test",
        }
    )
    repo.append_alert(
        {
            "type": "bias_change",
            "severity": "watch",
            "message": "Bias flipped",
            "symbol": "BTCUSDT",
            "delivered": False,
        }
    )
    session = get_session()
    try:
        score = session.query(MarketScore).one()
        assert score.bias_score == 42.0
        assert score.data_quality == 88.0
        dec = session.query(AIDecisionRecord).one()
        assert dec.market_bias == "Bullish"
        assert "Trend continuation" in (dec.narrative or "")
        rep = session.query(ReportRecord).one()
        assert rep.report_id == rid
        assert session.query(AlertRecord).count() == 1
    finally:
        session.close()


def test_data_package_shape():
    repo = CentralRepository()
    repo.append_spot({"symbol": "BTCUSDT", "price": 64000.0, "timestamp": datetime.now(timezone.utc).isoformat()})
    repo.append_market_score(
        {
            "symbol": "BTCUSDT",
            "market_bias_score": 10.0,
            "confidence_score": 60.0,
            "risk_score": 40.0,
            "data_quality_score": 80.0,
            "market_bias": "Neutral",
        }
    )
    pkg = build_data_package(symbol="BTCUSDT")
    assert pkg["asset"] == "BTCUSDT"
    assert "market_data" in pkg
    assert "analysis" in pkg
    assert "scores" in pkg
    assert "decision" in pkg
    assert pkg["scores"].get("bias_score") == 10.0
    assert "spot" in pkg["market_data"]


def test_tick_retention():
    from src.db.models import MarketCandle
    from src.db.seed import resolve_exchange_id, resolve_symbol_id

    session = get_session()
    try:
        ex = resolve_exchange_id(session, "binance")
        sym = resolve_symbol_id(session, "BTCUSDT")
        session.add(
            MarketCandle(
                exchange_id=ex,
                symbol_id=sym,
                timeframe="tick",
                timestamp=datetime.now(timezone.utc) - timedelta(days=30),
                open=1,
                high=1,
                low=1,
                close=1,
                volume=0,
            )
        )
        session.commit()
    finally:
        session.close()

    deleted = apply_retention()
    assert deleted.get("tick_candles", 0) >= 1
