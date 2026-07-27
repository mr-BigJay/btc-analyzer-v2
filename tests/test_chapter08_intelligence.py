"""Chapter 8 Market Intelligence Framework tests."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/btc_analyzer_ch8_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""

from src.ai.engine import AIDecisionEngine  # noqa: E402
from src.analysis.contracts import MarketAnalysisOutput  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402
from src.intelligence.contracts import MarketCycle, MarketRegime  # noqa: E402
from src.intelligence.engine import MarketIntelligenceEngine  # noqa: E402
from src.intelligence.regime import classify_regime  # noqa: E402


def setup_module():
    reset_engine()
    init_db(seed=True)


def _bullish_analysis(**overrides) -> MarketAnalysisOutput:
    base = MarketAnalysisOutput(
        market_bias="Bullish",
        confidence=74,
        market_regime="Trend",
        volatility="Medium",
        primary_scenario="Bullish Continuation",
        risk_level="Moderate",
        layer_results=[
            {
                "layer": "Spot",
                "signal": "Bullish",
                "confidence": 78,
                "summary": "Strong spot buying / accumulation",
                "tags": ["Buyer Dominance", "Accumulation"],
                "data_quality": 1.0,
                "details": {"large_trade_buy_usd": 5e6, "large_trade_sell_usd": 1e6, "mark_price": 65000},
            },
            {
                "layer": "Futures",
                "signal": "Bullish",
                "confidence": 72,
                "summary": "Open Interest increasing alongside positive Funding.",
                "tags": ["Leveraged Bullish"],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Options",
                "signal": "Bullish",
                "confidence": 70,
                "summary": "Dealer support / bullish hedging",
                "tags": ["Dealer Support", "Bullish Hedging"],
                "data_quality": 0.95,
                "details": {},
            },
            {
                "layer": "Technical",
                "signal": "Bullish",
                "confidence": 72,
                "summary": "Trend strength with breakout probability",
                "tags": ["Trend Strength", "Breakout Probability"],
                "data_quality": 1.0,
                "details": {"atr": 600, "mark_price": 65000},
            },
            {
                "layer": "Market Structure",
                "signal": "Bullish",
                "confidence": 76,
                "summary": "HH/HL intact",
                "tags": ["Bullish Structure", "BOS", "Trend Strength"],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Pattern Detection",
                "signal": "Bullish",
                "confidence": 55,
                "summary": "Bull flag",
                "tags": [],
                "data_quality": 0.7,
                "details": {},
            },
            {
                "layer": "Volatility",
                "signal": "Neutral",
                "confidence": 58,
                "summary": "Normal volatility",
                "tags": [],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Liquidity",
                "signal": "Bullish",
                "confidence": 62,
                "summary": "Liquidity above price",
                "tags": ["Liquidity Above"],
                "data_quality": 0.85,
                "details": {"liquidity_above": [66000], "liquidity_below": [64000]},
            },
        ],
        scenarios=[
            {"name": "Bullish Continuation", "probability": 60, "trigger": "Hold", "target_zones": [66000], "invalidation": 63500},
            {"name": "Sideways Consolidation", "probability": 25, "trigger": "Range", "target_zones": []},
            {"name": "Bearish Reversal", "probability": 15, "trigger": "Break", "target_zones": [], "invalidation": 66500},
        ],
        weights={
            "Spot": 0.2,
            "Futures": 0.2,
            "Options": 0.2,
            "Technical": 0.15,
            "Market Structure": 0.1,
            "Liquidity": 0.07,
            "Pattern Detection": 0.05,
            "Volatility": 0.03,
        },
        conflicts=[],
        symbol="BTCUSDT",
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_regime_strong_uptrend():
    analysis = _bullish_analysis().to_dict()
    regime, scores = classify_regime(analysis)
    assert regime in {
        MarketRegime.STRONG_UPTREND.value,
        MarketRegime.WEAK_UPTREND.value,
        MarketRegime.EXPANSION.value,
    }
    assert scores[regime] >= max(scores.values()) - 1e-9


def test_intelligence_output_schema():
    out = MarketIntelligenceEngine().evaluate(
        analysis=_bullish_analysis(), persist=False, multi_timeframe=False
    )
    d = out.to_dict()
    assert d["market_regime"]
    assert d["market_cycle"] in {c.value for c in MarketCycle}
    assert 0 <= d["market_health_index"] <= 100
    assert d["market_stress_index"] in {"Low", "Moderate", "Elevated", "High", "Extreme"}
    assert d["dominant_participant"]
    assert d["institutional_activity"] in {"Buying", "Selling", "Neutral Activity"}
    assert 0 <= d["transition_probability"] <= 100
    assert d["liquidity_state"]
    assert d["volatility_regime"]
    assert d["macro_bias"]
    assert d["cross_asset_bias"]


def test_short_squeeze_derivatives_thesis():
    analysis = _bullish_analysis()
    # Force futures summary pattern for short squeeze relational thesis
    for row in analysis.layer_results:
        if row["layer"] == "Futures":
            row["summary"] = "Open Interest increasing with Negative Funding while price rises"
            row["tags"] = ["Negative Funding", "Leveraged Bullish"]
    out = MarketIntelligenceEngine().evaluate(analysis=analysis, persist=False, multi_timeframe=False)
    assert "Short Squeeze" in out.derivatives_thesis or "short" in out.derivatives_thesis.lower()


def test_deterministic_intelligence():
    analysis = _bullish_analysis()
    a = MarketIntelligenceEngine().evaluate(analysis=analysis, persist=False, multi_timeframe=False).to_dict()
    b = MarketIntelligenceEngine().evaluate(analysis=analysis, persist=False, multi_timeframe=False).to_dict()
    a.pop("analyzed_at", None)
    b.pop("analyzed_at", None)
    assert a == b


def test_ai_uses_intelligence_regime():
    analysis = _bullish_analysis()
    intel = MarketIntelligenceEngine().evaluate(analysis=analysis, persist=False, multi_timeframe=False)
    report = AIDecisionEngine().decide(
        analysis=analysis, intelligence=intel, persist=False, multi_timeframe=False
    )
    assert report.market_regime == intel.market_regime
    assert report.market_intelligence.get("market_cycle") == intel.market_cycle
    assert abs(sum(s["probability"] for s in report.scenarios) - 100.0) < 0.2


def test_msi_can_force_no_trade():
    analysis = _bullish_analysis(confidence=80)
    intel = MarketIntelligenceEngine().evaluate(analysis=analysis, persist=False, multi_timeframe=False)
    intel.market_stress_index = "Extreme"
    intel.market_stress_score = 90
    report = AIDecisionEngine().decide(
        analysis=analysis, intelligence=intel, persist=False, multi_timeframe=False
    )
    assert report.trading_plan["preferred_direction"] == "no_trade"
