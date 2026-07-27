"""Unit tests for Ch.3 validation, normalization, quality, retry helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from src.collectors.common import RequestQueue, RetryHandler, TokenBucketLimiter
from src.pipeline.normalization import DataNormalizer, normalize_symbol
from src.pipeline.quality import DataQualityGate
from src.pipeline.validation import DataValidator


def test_normalize_symbol_variants():
    assert normalize_symbol("BTC-USDT") == "BTCUSDT"
    assert normalize_symbol("BTC_USDT") == "BTCUSDT"
    assert normalize_symbol("btc/usdt") == "BTCUSDT"
    assert normalize_symbol("BTC") == "BTCUSDT"
    assert normalize_symbol("BTC-PERPETUAL") == "BTCUSDT"


def test_normalizer_standard_fields():
    n = DataNormalizer()
    rec = n.normalize_record(
        "binance",
        {
            "symbol": "BTC-USDT",
            "price": "65000.5",
            "volume": 12,
            "timestamp": "2026-07-27T12:00:00+00:00",
            "funding_rate": 0.0001,
        },
    )
    assert rec.symbol == "BTCUSDT"
    assert rec.exchange == "binance"
    assert rec.price == 65000.5
    assert rec.source_id
    d = rec.to_dict()
    assert set(d) >= {"timestamp", "symbol", "exchange", "price", "volume", "source_id"}


def test_validator_rejects_nan_and_missing():
    v = DataValidator()
    report = v.validate(
        "binance",
        {
            "status": "OK",
            "symbol": "BTCUSDT",
            "mark_price": float("nan"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "_required_fields": ["mark_price", "symbol"],
        },
    )
    assert report.ok is False
    codes = {i.code for i in report.issues}
    assert "INVALID_VALUE" in codes


def test_validator_duplicate_records():
    v = DataValidator()
    report = v.validate(
        "binance",
        {
            "status": "OK",
            "symbol": "BTCUSDT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "records": [
                {"source_id": "a", "price": 1},
                {"source_id": "a", "price": 2},
            ],
        },
    )
    assert any(i.code == "DUPLICATE" for i in report.issues)


def test_quality_degrades_stale_cached():
    gate = DataQualityGate()
    q = gate.assess(
        {
            "timestamp": "2020-01-01T00:00:00+00:00",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "price": 100.0,
            "source_id": "x",
        },
        source_live=False,
    )
    assert q.degraded is True
    assert q.confidence < 1.0
    assert q.timely is False


def test_token_bucket_and_priority_queue():
    limiter = TokenBucketLimiter(rate_per_sec=100.0, capacity=1.0, tokens=0.0)
    wait = limiter.acquire(1.0)
    assert wait >= 0.0

    q = RequestQueue()
    q.enqueue("bg", background=True)
    q.enqueue("crit", critical=True)
    q.enqueue("normal")
    first = q.dequeue()
    assert first is not None
    assert first.critical is True


def test_retry_handler_eventually_succeeds():
    attempts = {"n": 0}

    async def flaky():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RuntimeError("fail")
        return "ok"

    async def run():
        handler = RetryHandler(delays_sec=(0.01, 0.01, 0.01))
        value, retries, err = await handler.run("test", "/ping", flaky)
        return value, retries, err

    value, retries, err = asyncio.run(run())
    assert value == "ok"
    assert err is None
    assert retries >= 1


def test_normalize_snapshot_merges_sources():
    n = DataNormalizer()
    snap = n.normalize(
        {
            "binance": {
                "symbol": "BTC_USDT",
                "mark_price": 70000,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "bitunix": {
                "symbol": "BTCUSDT",
                "price": 69999,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    )
    assert snap.symbol == "BTCUSDT"
    assert snap.price == 70000  # Binance is primary — Bitunix must not override
    assert snap.bitunix.get("price") == 69999
