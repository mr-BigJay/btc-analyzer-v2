"""Chapter 7 AI Decision Engine tests."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/btc_analyzer_ch7_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""

from src.ai.engine import AIDecisionEngine  # noqa: E402
from src.ai.evidence import aggregate_evidence  # noqa: E402
from src.ai.narrative import detect_narrative  # noqa: E402
from src.analysis.contracts import MarketAnalysisOutput  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402


def setup_module():
    reset_engine()
    init_db(seed=True)


def _analysis(**overrides) -> MarketAnalysisOutput:
    base = MarketAnalysisOutput(
        market_bias="Bullish",
        confidence=72,
        market_regime="Trend",
        volatility="Medium",
        primary_scenario="Bullish Continuation",
        risk_level="Moderate",
        layer_results=[
            {
                "layer": "Spot",
                "signal": "Bullish",
                "confidence": 75,
                "summary": "Strong buying pressure",
                "tags": ["Buyer Dominance", "Accumulation"],
                "data_quality": 1.0,
                "details": {"mark_price": 65000},
            },
            {
                "layer": "Futures",
                "signal": "Bullish",
                "confidence": 70,
                "summary": "Open Interest increasing alongside positive Funding.",
                "tags": ["Leveraged Bullish"],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Options",
                "signal": "Bullish",
                "confidence": 68,
                "summary": "Dealers hedging upside",
                "tags": ["Dealer Support", "Bullish Hedging"],
                "data_quality": 0.9,
                "details": {},
            },
            {
                "layer": "Technical",
                "signal": "Bullish",
                "confidence": 65,
                "summary": "Breakout confirmed",
                "tags": ["Trend Strength", "Breakout Probability"],
                "data_quality": 1.0,
                "details": {"atr": 650.0, "mark_price": 65000, "rsi": 58},
            },
            {
                "layer": "Market Structure",
                "signal": "Bullish",
                "confidence": 70,
                "summary": "HH/HL structure intact",
                "tags": ["Bullish Structure", "BOS"],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Pattern Detection",
                "signal": "Neutral",
                "confidence": 45,
                "summary": "No high-confidence pattern",
                "tags": [],
                "data_quality": 0.7,
                "details": {},
            },
            {
                "layer": "Volatility",
                "signal": "Neutral",
                "confidence": 55,
                "summary": "Moderate volatility",
                "tags": [],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Liquidity",
                "signal": "Bullish",
                "confidence": 60,
                "summary": "Liquidity above current price",
                "tags": ["Liquidity Above"],
                "data_quality": 0.8,
                "details": {"liquidity_above": [66000], "liquidity_below": [64000]},
            },
        ],
        scenarios=[
            {"name": "Bullish Continuation", "probability": 58, "trigger": "Hold HL", "target_zones": [66000, 67000], "invalidation": 63500},
            {"name": "Sideways Consolidation", "probability": 27, "trigger": "Range", "target_zones": [64500, 65500]},
            {"name": "Bearish Reversal", "probability": 15, "trigger": "Break HL", "target_zones": [63000], "invalidation": 66500},
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


def test_evidence_prioritization_orders_high_quality_first():
    analysis = _analysis()
    evidence = aggregate_evidence(analysis)
    assert len(evidence) == 8
    assert evidence[0].priority >= evidence[-1].priority


def test_narrative_bullish_trend_expansion():
    analysis = _analysis()
    evidence = aggregate_evidence(analysis)
    narrative, bullets = detect_narrative(analysis, evidence)
    assert narrative == "Bullish Trend Expansion"
    assert bullets


def test_ai_decision_probabilities_sum_100():
    report = AIDecisionEngine().decide(analysis=_analysis(), persist=False, multi_timeframe=False)
    total = sum(s["probability"] for s in report.scenarios)
    assert abs(total - 100.0) < 0.15
    dist_total = sum(report.probability_distribution.values())
    assert abs(dist_total - 100.0) < 0.15
    assert report.reasoning.get("primary_conclusion")
    assert report.daily_outlook.get("executive_summary")
    assert report.trading_plan.get("preferred_direction") in {"long", "short", "no_trade"}
    assert "guarantee" not in report.disclaimer.lower() or "not guarantees" in report.disclaimer.lower()


def test_deterministic_identical_inputs():
    analysis = _analysis()
    a = AIDecisionEngine().decide(analysis=analysis, persist=False, multi_timeframe=False)
    b = AIDecisionEngine().decide(analysis=analysis, persist=False, multi_timeframe=False)
    assert a.analysis_fingerprint == b.analysis_fingerprint
    assert a.market_bias == b.market_bias
    assert a.primary_narrative == b.primary_narrative
    assert a.confidence == b.confidence
    assert a.scenarios == b.scenarios
    assert a.daily_outlook["executive_summary"] == b.daily_outlook["executive_summary"]


def test_conflict_explanation_present():
    analysis = _analysis(
        conflicts=["Contradictory clusters: bullish=['Spot'] bearish=['Futures']"],
        layer_results=[
            {
                "layer": "Spot",
                "signal": "Bullish",
                "confidence": 80,
                "summary": "Strong spot demand",
                "tags": ["Buyer Dominance"],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Futures",
                "signal": "Bearish",
                "confidence": 78,
                "summary": "Leveraged positioning bearish",
                "tags": ["Leveraged Bearish", "Long Squeeze Risk"],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Options",
                "signal": "Bullish",
                "confidence": 70,
                "summary": "Institutional upside hedges",
                "tags": ["Bullish Hedging"],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Technical",
                "signal": "Neutral",
                "confidence": 50,
                "summary": "Mixed",
                "tags": [],
                "data_quality": 1.0,
                "details": {"atr": 500},
            },
            {
                "layer": "Market Structure",
                "signal": "Neutral",
                "confidence": 50,
                "summary": "Range",
                "tags": [],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Pattern Detection",
                "signal": "Neutral",
                "confidence": 40,
                "summary": "None",
                "tags": [],
                "data_quality": 0.5,
                "details": {},
            },
            {
                "layer": "Volatility",
                "signal": "Neutral",
                "confidence": 50,
                "summary": "Normal",
                "tags": [],
                "data_quality": 1.0,
                "details": {},
            },
            {
                "layer": "Liquidity",
                "signal": "Neutral",
                "confidence": 50,
                "summary": "Balanced",
                "tags": [],
                "data_quality": 0.8,
                "details": {},
            },
        ],
    )
    report = AIDecisionEngine().decide(analysis=analysis, persist=False, multi_timeframe=False)
    assert report.reasoning.get("conflict_narrative")
    assert "Conflicting" in report.reasoning["conflict_narrative"] or report.reasoning.get("conflicting_evidence")


def test_no_trade_when_uncertainty_high():
    analysis = _analysis(market_bias="High Uncertainty", confidence=35, conflicts=["mixed"])
    report = AIDecisionEngine().decide(analysis=analysis, persist=False, multi_timeframe=False)
    assert report.trading_plan["preferred_direction"] == "no_trade"
    assert report.confidence < 60 or report.reasoning.get("uncertainty_note")
