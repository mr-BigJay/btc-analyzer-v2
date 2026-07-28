"""Chapter 13 — Feature Engineering tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

TEST_DB = Path("/tmp/btc_analyzer_ch13_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""

from src.analysis.context import MarketContext  # noqa: E402
from src.config import settings  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402
from src.features.cleaning import drop_invalid_ohlcv  # noqa: E402
from src.features.contracts import FEATURE_SCHEMA_VERSION, FeatureCategory, FeatureRecord, FeatureScale  # noqa: E402
from src.features.engine import FeatureEngineeringEngine  # noqa: E402
from src.features.normalize import apply_scale, normalize_directional, normalize_probability  # noqa: E402
from src.features.outliers import detect_outliers  # noqa: E402
from src.features.store import feature_store_memory  # noqa: E402
from src.features.validation import feature_quarantine, validate_feature  # noqa: E402
from src.scoring.quality import compute_dqs  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh():
    reset_engine()
    if TEST_DB.exists():
        TEST_DB.unlink()
    settings.database_url = f"sqlite:///{TEST_DB}"
    init_db(seed=True)
    feature_store_memory.clear()
    feature_quarantine.clear()
    yield
    reset_engine()


def _synth_ohlcv(n: int = 80, start: float = 60000.0) -> list[dict]:
    rows = []
    px = start
    for i in range(n):
        px = px * (1.0 + (0.001 if i % 3 else -0.0007))
        rows.append(
            {
                "open": px * 0.999,
                "high": px * 1.002,
                "low": px * 0.998,
                "close": px,
                "volume": 100 + i,
            }
        )
    return rows


def test_normalization_scales():
    assert normalize_directional(0.5, scale=1.0) == 50.0
    assert normalize_probability(0.5) == 50.0
    assert apply_scale(120, FeatureScale.DIRECTIONAL.value) == 100.0
    assert apply_scale(-2, FeatureScale.RATIO.value) == 0.0


def test_cleaning_drops_invalid_and_no_fabrication():
    rows = drop_invalid_ohlcv(
        [
            {"open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1},
            {"open": -1, "high": 2, "low": 0.5, "close": 1.5},
            {"open": 1, "high": float("nan"), "low": 0.5, "close": 1.5},
        ]
    )
    assert len(rows) == 1


def test_outlier_flags_not_removed():
    flags = detect_outliers({"price": -1, "funding_rate": 0.1, "volume": 1})
    codes = {f.code for f in flags}
    assert "NEGATIVE_PRICE" in codes
    assert "FUNDING_SPIKE" in codes


def test_feature_validation_quarantines_non_finite():
    from src.features.contracts import FeatureRecord as FR

    rec = FR(
        name="bad",
        value=float("inf"),
        category=FeatureCategory.PRICE.value,
        scale=FeatureScale.RAW.value,
    )
    report = validate_feature(rec)
    assert report.ok is False


def test_engine_produces_versioned_feature_set():
    ctx = MarketContext(
        symbol="BTCUSDT",
        timeframe="1h",
        mark_price=65000,
        funding_rate=0.0001,
        open_interest=1000,
        put_call_ratio=0.9,
        ohlcv=_synth_ohlcv(),
        order_book={"bids": [[64900, 1.0]], "asks": [[65100, 1.2]]},
    )
    fs = FeatureEngineeringEngine().engineer(ctx, persist=True, multi_timeframe=False)
    assert fs.schema_version == FEATURE_SCHEMA_VERSION
    assert fs.feature_version
    assert fs.calculation_engine
    assert "market_pressure_index" in fs.features or "market_pressure_index" in fs.composites
    assert "price_strength" in fs.outputs
    assert fs.elapsed_ms is not None
    # Lineage present
    sample = next(iter(fs.features.values()))
    assert sample.lineage is not None
    assert sample.lineage.feature
    # Stored in memory
    assert feature_store_memory.get("BTCUSDT", "1h") is not None


def test_missing_data_reduces_quality_and_dqs():
    # Sparse context → many missing features
    ctx = MarketContext(symbol="BTCUSDT", timeframe="1h", ohlcv=[])
    fs = FeatureEngineeringEngine().engineer(ctx, persist=False, multi_timeframe=False)
    assert fs.missing_count > 0
    assert fs.data_quality < 1.0

    dqs_low, _, details = compute_dqs(
        {"layer_results": [{"data_quality": 0.8, "summary": "x"}] * 8, "confidence": 60},
        feature_set=fs.to_dict(),
    )
    dqs_high, _, _ = compute_dqs(
        {"layer_results": [{"data_quality": 0.8, "summary": "x"}] * 8, "confidence": 60},
        feature_set={"data_quality": 1.0, "missing_count": 0},
    )
    assert details.get("feature_penalty", 0) >= 0
    assert dqs_low <= dqs_high


def test_features_api_engineer():
    from fastapi.testclient import TestClient

    from src.api.app import app
    from src.storage.redis_cache import redis_cache

    redis_cache.set(
        "technical_cache_1h",
        {"ohlcv": _synth_ohlcv(), "spot": {"price": 65000, "volume": 10}},
        ttl_sec=60,
    )
    client = TestClient(app)
    r = client.post("/api/v1/features/engineer?symbol=BTCUSDT&timeframe=1h")
    assert r.status_code == 200
    body = r.json()
    data = body.get("data") or body
    assert data.get("asset") == "BTCUSDT"
    assert "outputs" in data
