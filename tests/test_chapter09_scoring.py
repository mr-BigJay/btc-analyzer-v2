"""Chapter 9 Scoring & Decision Model tests."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/btc_analyzer_ch9_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""

from src.analysis.contracts import MarketAnalysisOutput  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402
from src.intelligence.engine import MarketIntelligenceEngine  # noqa: E402
from src.scoring.composites import MATRIX_WEIGHTS, market_bias_score  # noqa: E402
from src.scoring.contracts import classify_bias  # noqa: E402
from src.scoring.engine import ScoringEngine  # noqa: E402
from src.scoring.layers import score_all_layers  # noqa: E402
from src.scoring.weights import DEFAULT_WEIGHTS, RANGE_WEIGHTS, TREND_WEIGHTS, select_weights  # noqa: E402


def setup_module():
    reset_engine()
    init_db(seed=True)


def _analysis(bullish: bool = True) -> MarketAnalysisOutput:
    sig = "Bullish" if bullish else "Bearish"
    return MarketAnalysisOutput(
        market_bias=sig,
        confidence=70,
        market_regime="Trend" if bullish else "Range",
        volatility="Medium",
        primary_scenario="Bullish Continuation" if bullish else "Bearish Reversal",
        risk_level="Moderate",
        layer_results=[
            {"layer": "Spot", "signal": sig, "confidence": 75, "summary": "spot", "tags": ["Buyer Dominance"] if bullish else ["Seller Dominance"], "data_quality": 1.0, "details": {}},
            {"layer": "Futures", "signal": sig, "confidence": 70, "summary": "fut", "tags": ["Leveraged Bullish"] if bullish else ["Leveraged Bearish"], "data_quality": 1.0, "details": {}},
            {"layer": "Options", "signal": sig, "confidence": 68, "summary": "opt", "tags": ["Dealer Support"] if bullish else ["Dealer Resistance"], "data_quality": 0.9, "details": {}},
            {"layer": "Technical", "signal": sig, "confidence": 72, "summary": "tech", "tags": ["Trend Strength"], "data_quality": 1.0, "details": {"atr": 500}},
            {"layer": "Market Structure", "signal": sig, "confidence": 74, "summary": "struct", "tags": ["Bullish Structure", "BOS"] if bullish else ["Bearish Structure"], "data_quality": 1.0, "details": {}},
            {"layer": "Pattern Detection", "signal": "Neutral", "confidence": 45, "summary": "pat", "tags": [], "data_quality": 0.7, "details": {}},
            {"layer": "Volatility", "signal": "Neutral", "confidence": 55, "summary": "vol", "tags": [], "data_quality": 1.0, "details": {}},
            {"layer": "Liquidity", "signal": sig, "confidence": 60, "summary": "liq", "tags": ["Liquidity Above"] if bullish else ["Liquidity Below"], "data_quality": 0.8, "details": {}},
        ],
        scenarios=[
            {"name": "Bullish Continuation", "probability": 55, "trigger": "t", "target_zones": []},
            {"name": "Sideways Consolidation", "probability": 30, "trigger": "t", "target_zones": []},
            {"name": "Bearish Reversal", "probability": 15, "trigger": "t", "target_zones": []},
        ],
        weights=dict(DEFAULT_WEIGHTS),
        conflicts=[],
        timeframe_alignment={"aligned": True, "biases": {"1h": sig, "4h": sig}},
        symbol="BTCUSDT",
    )


def test_matrix_weights_sum_to_one():
    assert abs(sum(MATRIX_WEIGHTS.values()) - 1.0) < 1e-9


def test_layer_scores_in_range():
    scores = score_all_layers(_analysis())
    assert set(scores) >= {"Spot", "Futures", "Options", "Technical"}
    for v in scores.values():
        assert -100 <= v <= 100


def test_regime_weights_tables():
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9
    assert abs(sum(TREND_WEIGHTS.values()) - 1.0) < 1e-9
    assert abs(sum(RANGE_WEIGHTS.values()) - 1.0) < 1e-9
    w, key = select_weights(market_regime="Strong Uptrend")
    assert key == "trend"
    assert abs(sum(w.values()) - 1.0) < 1e-6


def test_classify_bias_thresholds():
    assert classify_bias(80) == "Strong Bullish"
    assert classify_bias(50) == "Bullish"
    assert classify_bias(20) == "Slightly Bullish"
    assert classify_bias(0) == "Neutral"
    assert classify_bias(-20) == "Slightly Bearish"
    assert classify_bias(-50) == "Bearish"
    assert classify_bias(-80) == "Strong Bearish"


def test_mbs_positive_on_bullish_stack():
    scores = score_all_layers(_analysis(True))
    mbs = market_bias_score(scores, DEFAULT_WEIGHTS)
    assert mbs > 15


def test_scoring_engine_decision_object():
    analysis = _analysis(True)
    intel = MarketIntelligenceEngine().evaluate(analysis=analysis, persist=False, multi_timeframe=False)
    decision = ScoringEngine().score(
        analysis=analysis, intelligence=intel, persist=False, multi_timeframe=False
    )
    d = decision.to_dict()
    assert "market_bias" in d and "market_bias_score" in d
    assert 0 <= d["confidence_score"] <= 100
    assert 0 <= d["risk_score"] <= 100
    assert 0 <= d["data_quality_score"] <= 100
    assert isinstance(d["publish"], bool)
    assert d["decision"] == d["market_bias"]
    assert abs(sum(d["weights"].values()) - 1.0) < 1e-5


def test_conflict_penalty_reduces_confidence():
    analysis = _analysis(True)
    # Force Spot vs Futures conflict
    for row in analysis.layer_results:
        if row["layer"] == "Futures":
            row["signal"] = "Bearish"
            row["confidence"] = 80
            row["tags"] = ["Leveraged Bearish"]
    intel = MarketIntelligenceEngine().evaluate(analysis=analysis, persist=False, multi_timeframe=False)
    aligned = ScoringEngine().score(analysis=_analysis(True), intelligence=intel, persist=False)
    conflicted = ScoringEngine().score(analysis=analysis, intelligence=intel, persist=False)
    assert conflicted.conflict_penalties
    assert conflicted.confidence_score <= aligned.confidence_score + 5


def test_deterministic_scoring():
    analysis = _analysis(True)
    intel = MarketIntelligenceEngine().evaluate(analysis=analysis, persist=False, multi_timeframe=False)
    a = ScoringEngine().score(analysis=analysis, intelligence=intel, persist=False).to_dict()
    b = ScoringEngine().score(analysis=analysis, intelligence=intel, persist=False).to_dict()
    a.pop("scored_at", None)
    b.pop("scored_at", None)
    assert a == b
