"""Chapter 5 API envelope + services smoke tests."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/btc_analyzer_ch5_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""
os.environ["API_RATE_LIMIT_PER_MINUTE"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402

from src.api.app import app  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402
from src.services import AnalysisService, MarketService  # noqa: E402


def setup_module():
    reset_engine()
    init_db(seed=True)


def test_health_envelope_and_request_id():
    client = TestClient(app)
    r = client.get("/api/v1/health", headers={"X-Request-ID": "test-cid-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["request_id"] == "test-cid-1"
    assert "timestamp" in body
    assert body["data"]["chapter"] == "17-dashboard-ux"
    assert r.headers.get("X-Request-ID") == "test-cid-1"
    assert "X-Content-Type-Options" in r.headers


def test_architecture_and_market_snapshot():
    client = TestClient(app)
    arch = client.get("/api/v1/architecture").json()
    assert arch["status"] == "success"
    assert arch["data"]["scheduler"]["15m"] == "pattern_detection"
    assert arch["data"]["backend"]["logging"] == "loguru"

    snap = client.get("/api/v1/market/snapshot").json()
    assert snap["status"] == "success"
    assert "mark_price" in snap["data"]


def test_analysis_service_pattern_isolated():
    result = AnalysisService().detect_patterns()
    assert result["engine"] == "pattern"
    assert result["status"] in {"OK", "SKIPPED"}
    market = MarketService().snapshot()
    assert "cache_backend" in market
