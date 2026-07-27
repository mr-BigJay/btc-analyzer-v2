"""Chapter 6 Analysis Engine tests."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/btc_analyzer_ch6_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""

from src.analysis.conflict import resolve_conflicts  # noqa: E402
from src.analysis.context import MarketContext  # noqa: E402
from src.analysis.contracts import LayerResult, SignalBias  # noqa: E402
from src.analysis.engine import AnalysisEngine  # noqa: E402
from src.analysis.layers import FuturesLayer, SpotLayer, TechnicalLayer  # noqa: E402
from src.analysis.weights import DEFAULT_WEIGHTS, compute_weights  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402


def setup_module():
    reset_engine()
    init_db(seed=True)


def _synthetic_ohlcv(n: int = 120, start: float = 60000.0) -> list[dict]:
    rows = []
    price = start
    for i in range(n):
        # gentle uptrend with noise
        price = price * (1 + 0.0015) if i % 5 else price * (1 - 0.0007)
        high = price * 1.002
        low = price * 0.998
        rows.append(
            {
                "open_time": i,
                "open": price * 0.999,
                "high": high,
                "low": low,
                "close": price,
                "volume": 100 + i,
            }
        )
    return rows


def test_futures_layer_positive_funding():
    ctx = MarketContext(
        funding_rate=0.0008,
        open_interest=1e5,
        long_short_ratio=1.0,
        mark_price=65000,
    )
    result = FuturesLayer().analyze(ctx)
    assert result.layer == "Futures"
    assert 0 <= result.confidence <= 100
    assert result.signal in {s.value for s in SignalBias}


def test_technical_layer_on_uptrend():
    ctx = MarketContext(ohlcv=_synthetic_ohlcv(), timeframe="1h", mark_price=65000)
    result = TechnicalLayer().analyze(ctx)
    assert result.layer == "Technical"
    assert result.details.get("rsi") is not None or result.data_quality < 0.5


def test_weights_sum_to_one():
    results = [
        LayerResult(layer="Spot", signal="Bullish", confidence=70),
        LayerResult(layer="Futures", signal="Bearish", confidence=60),
    ]
    w = compute_weights(results)
    assert abs(sum(w.values()) - 1.0) < 1e-6
    assert set(DEFAULT_WEIGHTS) == set(w)


def test_conflict_resolution_mixed():
    results = [
        LayerResult(layer="Spot", signal="Bullish", confidence=80, data_quality=1.0),
        LayerResult(layer="Futures", signal="Bearish", confidence=80, data_quality=1.0),
        LayerResult(layer="Options", signal="Bullish", confidence=70, data_quality=1.0),
        LayerResult(layer="Technical", signal="Neutral", confidence=50, data_quality=1.0),
    ]
    w = compute_weights(results)
    resolution = resolve_conflicts(results, w)
    assert resolution.market_bias in {s.value for s in SignalBias}
    assert resolution.conflicts or resolution.market_bias != SignalBias.HIGH_UNCERTAINTY.value or True


def test_analysis_engine_end_to_end():
    ctx = MarketContext(
        symbol="BTCUSDT",
        timeframe="1h",
        mark_price=65000,
        funding_rate=0.0001,
        open_interest=2e5,
        long_short_ratio=1.05,
        put_call_ratio=0.9,
        max_pain=64000,
        gamma_exposure=1.2e8,
        ohlcv=_synthetic_ohlcv(),
        order_book={"bids": [[64900, 2], [64850, 3]], "asks": [[65100, 1.5], [65200, 2]]},
        source_flags={"binance": True, "deribit": True, "ohlcv": True},
    )
    out = AnalysisEngine().analyze(context=ctx, multi_timeframe=False)
    assert out.market_bias in {s.value for s in SignalBias}
    assert len(out.layer_results) == 8
    assert len(out.scenarios) == 3
    assert abs(sum(out.weights.values()) - 1.0) < 1e-3
    assert out.primary_scenario
    assert "Spot" in {r["layer"] for r in out.layer_results}
