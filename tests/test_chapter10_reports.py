"""Chapter 10 Report Generation & Intelligence Delivery tests."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/btc_analyzer_ch10_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""

from src.db.session import init_db, reset_engine  # noqa: E402
from src.reports.alerts import detect_alerts  # noqa: E402
from src.reports.audiences import render_for_audience  # noqa: E402
from src.reports.builder import build_report  # noqa: E402
from src.reports.channels.telegram import render_telegram  # noqa: E402
from src.reports.contracts import Audience, ReportType  # noqa: E402
from src.reports.qa import validate_report  # noqa: E402


def setup_module():
    reset_engine()
    init_db(seed=True)


def _ai_fixture() -> dict:
    return {
        "market_bias": "Bullish",
        "confidence": 82,
        "confidence_band": "Very High",
        "market_regime": "Strong Uptrend",
        "primary_narrative": "Bullish Trend Expansion",
        "primary_scenario": "Bullish Continuation",
        "risk_level": "Moderate Risk",
        "key_drivers": [
            "Strong Spot Accumulation",
            "Positive Dealer Gamma",
            "Rising Open Interest",
            "Bullish Market Structure",
            "Healthy Liquidity",
        ],
        "major_risks": ["Funding imbalance", "False breakout"],
        "scenarios": [
            {"name": "Bullish Continuation", "probability": 61, "trigger": "Hold HL", "invalidation": 64000},
            {"name": "Sideways Consolidation", "probability": 25, "trigger": "Range"},
            {"name": "Bearish Reversal", "probability": 14, "trigger": "Break", "invalidation": 67000},
        ],
        "trading_plan": {
            "preferred_direction": "long",
            "entry_zone": [65000, 65200],
            "confirmation_conditions": ["Hold support"],
            "target_levels": [66000, 67000],
            "stop_loss_zone": 64000,
            "position_sizing_guidance": "Risk ≤1%",
            "session_notes": "Advisory",
            "confidence": 82,
        },
        "reasoning": {
            "primary_conclusion": "Bullish bias supported by spot and options.",
            "supporting_evidence": ["Spot accumulation"],
            "conflicting_evidence": ["Futures leverage elevated"],
            "confidence_explanation": "Strong agreement",
            "risk_explanation": "Moderate leverage risk",
            "conflict_narrative": "Leverage rising while spot remains constructive.",
        },
        "daily_outlook": {
            "executive_summary": "Market is Bullish in a Strong Uptrend. Confidence 82%. Monitor spot accumulation.",
            "final_assessment": "Constructive outlook with defined invalidation.",
            "invalidation_levels": [64000],
        },
        "evidence": [
            {"layer": "Spot", "signal": "Bullish", "confidence": 80, "evidence": "Strong spot accumulation", "tags": ["Accumulation"]},
            {"layer": "Futures", "signal": "Bullish", "confidence": 70, "evidence": "OI rising", "tags": []},
            {"layer": "Options", "signal": "Bullish", "confidence": 75, "evidence": "Dealer support", "tags": ["Dealer Support"]},
        ],
        "market_intelligence": {
            "market_regime": "Strong Uptrend",
            "market_cycle": "Markup",
            "liquidity_state": "Liquidity Above",
            "volatility_regime": "Normal",
            "market_stress_index": "Moderate",
            "derivatives_thesis": "Aligned derivatives/spot stack",
        },
        "scoring": {
            "market_bias": "Bullish",
            "market_bias_score": 68,
            "confidence_score": 82,
            "risk_score": 31,
            "data_quality_score": 96,
            "layer_scores": {"Spot": 75, "Futures": 70, "Options": 72},
            "conflict_penalties": [{"pair": "Futures Conflict", "penalty": -6}],
            "details": {"confidence_meta": {"agreement_label": "Minor disagreement", "mtf_delta": 2, "mtf_alignment": "Partial Alignment"}},
        },
        "symbol": "BTCUSDT",
        "analyzed_at": "2026-07-27T00:00:00+00:00",
        "analysis_fingerprint": "abc123",
        "disclaimer": "Advisory only.",
    }


def test_build_daily_outlook_structure():
    report = build_report(ai_report=_ai_fixture(), audience=Audience.PROFESSIONAL.value)
    assert report.report_type == ReportType.DAILY_OUTLOOK.value
    assert report.market_bias == "Bullish"
    assert report.confidence == 82
    assert len(report.executive_summary.split()) <= 100
    assert report.primary_scenario.get("name") == "Bullish Continuation"
    assert report.trading_plan.get("direction") == "long"
    assert report.trading_plan.get("advisory") is True
    assert report.metadata.get("report_id")
    assert report.metadata.get("schema_version") == "10.0"


def test_qa_passes_valid_report():
    report = build_report(ai_report=_ai_fixture())
    qa = validate_report(report)
    assert qa["ok"] is True
    assert qa["publish"] is True


def test_qa_fails_missing_explanation_on_actionable_plan():
    ai = _ai_fixture()
    ai["reasoning"] = {}
    ai["daily_outlook"] = {"executive_summary": "", "final_assessment": ""}
    report = build_report(ai_report=ai)
    report.executive_summary = ""
    report.final_conclusion = ""
    report.explainability = {}
    qa = validate_report(report)
    assert qa["ok"] is False


def test_audience_executive_is_short():
    report = build_report(ai_report=_ai_fixture())
    view = render_for_audience(report, Audience.EXECUTIVE.value)
    assert "decision_object" not in view
    assert "ai_report" not in view
    assert "market_bias" in view
    assert set(view["trading_plan"].keys()) == {"direction"}


def test_audience_analyst_keeps_raw():
    report = build_report(ai_report=_ai_fixture())
    view = render_for_audience(report, Audience.ANALYST.value)
    assert view.get("decision_object")
    assert view.get("ai_report")
    assert view.get("confidence_breakdown")


def test_telegram_render_concise():
    report = build_report(ai_report=_ai_fixture())
    text = render_telegram(report, audience=Audience.EXECUTIVE.value)
    assert "Bullish" in text
    assert "82" in text
    assert "Advisory" in text or "advisory" in text.lower() or "guarantee" in text.lower() or "Disclaimer" in text or "disclaimer" in text.lower()


def test_scenario_probabilities_sum_near_100():
    report = build_report(ai_report=_ai_fixture())
    total = float(report.primary_scenario.get("probability") or 0) + sum(
        float(s.get("probability") or 0) for s in report.alternative_scenarios
    )
    assert abs(total - 100) < 0.1


def test_alerts_on_regime_change():
    current = {
        "market_regime": "Strong Uptrend",
        "confidence": 80,
        "market_intelligence": {"liquidity_state": "Liquidity Above", "derivatives_thesis": ""},
        "ai_report": {"evidence": []},
        "market_bias": "Bullish",
    }
    previous = {
        "market_regime": "Range",
        "confidence": 60,
        "market_intelligence": {},
    }
    alerts = detect_alerts(current=current, previous=previous)
    types = {a.alert_type for a in alerts}
    assert "Market Regime Changed" in types
    assert "Confidence Increased" in types
