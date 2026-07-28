"""Chapter 15 — Risk Management & Capital Preservation tests."""

from __future__ import annotations

from src.risk.contracts import RiskObject, crs_to_level
from src.risk.crs import CATEGORY_WEIGHTS, composite_risk_score
from src.risk.categories import (
    score_data_risk,
    score_event_risk,
    score_leverage_risk,
    score_liquidity_risk,
    score_market_risk,
    score_volatility_risk,
)
from src.risk.engine import RiskEngine
from src.risk.matrix import confidence_risk_guidance
from src.risk.no_trade import evaluate_no_trade_zone
from src.risk.sizing import exposure_from_crs, refine_exposure


def test_crs_bands():
    assert crs_to_level(0) == "Very Low"
    assert crs_to_level(20) == "Very Low"
    assert crs_to_level(21) == "Low"
    assert crs_to_level(40) == "Low"
    assert crs_to_level(41) == "Moderate"
    assert crs_to_level(60) == "Moderate"
    assert crs_to_level(61) == "High"
    assert crs_to_level(80) == "High"
    assert crs_to_level(81) == "Extreme"
    assert crs_to_level(100) == "Extreme"


def test_category_weights_sum_to_one():
    assert abs(sum(CATEGORY_WEIGHTS.values()) - 1.0) < 1e-9


def test_exposure_bands_from_crs():
    assert exposure_from_crs(10)[0] == "Full allocation"
    assert exposure_from_crs(30)[0] == "Moderate allocation"
    assert exposure_from_crs(50)[0] == "Reduced allocation"
    assert exposure_from_crs(70)[0] == "Minimal allocation"
    assert exposure_from_crs(90) == ("No new position", 0.0)


def test_confidence_risk_matrix():
    assert confidence_risk_guidance(80, 30) == "Favorable conditions"
    assert confidence_risk_guidance(80, 70) == "Opportunity with elevated caution"
    assert confidence_risk_guidance(50, 30) == "Wait for confirmation"
    assert confidence_risk_guidance(50, 70) == "Avoid new exposure"


def test_liquidity_maps_balanced_and_vacuum():
    healthy = score_liquidity_risk(
        intelligence={"liquidity_state": "Balanced"},
        analysis={},
    )
    assert healthy.label == "Healthy"
    vacuum = score_liquidity_risk(
        intelligence={"liquidity_state": "Liquidity Vacuum"},
        analysis={},
    )
    assert vacuum.label == "Critical"
    assert vacuum.score >= 80


def test_no_trade_zone_dqs_and_msi():
    ntz, reasons = evaluate_no_trade_zone(
        decision={"data_quality_score": 40, "publish": True},
        intelligence={"market_stress_index": "Extreme"},
        analysis={},
        crs=50,
        data_risk_score=20,
        event_risk_label="Low",
        liquidity_label="Healthy",
    )
    assert ntz is True
    assert any("Data Quality" in r for r in reasons)
    assert any("Market Stress" in r for r in reasons)


def test_no_trade_zone_extreme_crs():
    ntz, reasons = evaluate_no_trade_zone(
        decision={"data_quality_score": 90, "publish": True},
        intelligence={"market_stress_index": "Low"},
        analysis={},
        crs=85,
        data_risk_score=10,
        event_risk_label="Low",
        liquidity_label="Healthy",
    )
    assert ntz is True
    assert any("extreme" in r.lower() for r in reasons)


def test_risk_engine_deterministic():
    eng = RiskEngine()
    kwargs = dict(
        decision={"confidence_score": 78, "data_quality_score": 88, "publish": True, "market_bias": "Bullish"},
        intelligence={
            "market_stress_index": "Moderate",
            "liquidity_state": "Balanced",
            "volatility_regime": "Normal",
        },
        analysis={"market_bias": "Bullish", "layer_results": [{"layer": "Technical", "tags": []}]},
        persist=False,
    )
    a = eng.evaluate(**kwargs)
    b = eng.evaluate(**kwargs)
    assert a.composite_risk_score == b.composite_risk_score
    assert a.risk_level == b.risk_level
    assert a.explanation
    assert 0 <= a.composite_risk_score <= 100


def test_apply_to_trading_plan_forces_no_trade():
    eng = RiskEngine()
    risk = eng.evaluate(
        decision={"confidence_score": 40, "data_quality_score": 30, "publish": False},
        intelligence={"market_stress_index": "High", "liquidity_state": "Liquidity Vacuum", "volatility_regime": "Extreme"},
        analysis={"market_bias": "High Uncertainty", "conflicts": ["a", "b"], "layer_results": []},
        macro_event=True,
        persist=False,
    )
    assert risk.no_trade_zone is True
    assert risk.suppressed is True
    assert risk.exposure_fraction == 0.0
    plan = eng.apply_to_trading_plan(
        {"preferred_direction": "long", "session_notes": "", "confirmation_conditions": []},
        risk,
    )
    assert plan["preferred_direction"] == "no_trade"
    assert "risk_object" in plan
    assert "Risk Engine override" in plan["session_notes"]


def test_ai_cannot_bypass_risk_controls():
    """Even a bullish high-confidence plan is flattened when NTZ is active."""
    eng = RiskEngine()
    risk = RiskObject(
        composite_risk_score=88,
        risk_level="Extreme",
        no_trade_zone=True,
        no_trade_reasons=["Composite Risk Score extreme (88)"],
        suppressed=True,
        suppression_log=["Composite Risk Score extreme (88)"],
        exposure_fraction=0.0,
        suggested_exposure="No new position",
        capital_preservation_mode="Lockdown",
        explanation="No Trade Zone active.",
    )
    out = eng.apply_to_trading_plan({"preferred_direction": "long", "session_notes": "AI says long"}, risk)
    assert out["preferred_direction"] == "no_trade"
    assert "AI says long" in out["session_notes"]
    assert "Risk Engine override" in out["session_notes"]


def test_standard_risk_object_shape():
    eng = RiskEngine()
    obj = eng.evaluate(
        decision={"confidence_score": 70, "data_quality_score": 85, "publish": True},
        intelligence={"market_stress_index": "Low", "liquidity_state": "Healthy", "volatility_regime": "Low"},
        analysis={"market_bias": "Bullish", "layer_results": [{"layer": "Spot", "tags": []}] * 8},
        persist=False,
    )
    d = obj.to_dict()
    for key in (
        "composite_risk_score",
        "risk_level",
        "liquidity_state",
        "volatility_adjustment",
        "event_risk",
        "leverage_environment",
        "no_trade_zone",
        "capital_preservation_mode",
    ):
        assert key in d
    roundtrip = RiskObject.from_dict(d)
    assert roundtrip.composite_risk_score == obj.composite_risk_score


def test_refine_exposure_msi_lockdown():
    label, frac, mode = refine_exposure(
        crs=30,
        confidence=80,
        msi="Extreme",
        dqs=90,
        volatility_adjustment="No adjustment",
        no_trade=False,
    )
    assert frac == 0.0
    assert label == "No new position"
    assert mode == "Lockdown"


def test_category_scorers_smoke():
    market = score_market_risk(
        intelligence={"market_stress_index": "Elevated", "transition_probability": 70},
        analysis={"conflicts": ["x"]},
        decision={},
    )
    assert market.score > 40
    vol = score_volatility_risk(intelligence={"volatility_regime": "Extreme"}, analysis={})
    assert vol.label == "Significant reduction"
    event = score_event_risk(macro_event=True, near_options_expiry=True)
    assert event.label == "High"
    data = score_data_risk(decision={"data_quality_score": 40}, analysis={"layer_results": []})
    assert data.score >= 50
    lev = score_leverage_risk(
        intelligence={},
        analysis={"layer_results": [{"tags": ["Overcrowded Market"]}]},
        decision={},
    )
    assert "Elevated" in lev.label or "Extreme" in lev.label


def test_composite_uses_weights():
    from src.risk.contracts import CategoryScore

    cats = {name: CategoryScore(name, 100.0) for name in CATEGORY_WEIGHTS}
    crs, level, parts = composite_risk_score(cats)
    assert crs == 100.0
    assert level == "Extreme"
    assert set(parts) == set(CATEGORY_WEIGHTS)


def test_risk_api_status_and_evaluate():
    from fastapi.testclient import TestClient

    from src.api.app import app

    client = TestClient(app)
    r = client.get("/api/v1/risk/status")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["schema_version"]
    assert "deterministic" in body["governance"]

    r2 = client.post(
        "/api/v1/risk/evaluate",
        json={
            "decision": {"confidence_score": 75, "data_quality_score": 80, "publish": True},
            "intelligence": {
                "market_stress_index": "Low",
                "liquidity_state": "Balanced",
                "volatility_regime": "Normal",
            },
            "analysis": {"market_bias": "Bullish", "layer_results": [{"layer": "Technical", "tags": []}]},
            "persist": True,
        },
    )
    assert r2.status_code == 200
    data = r2.json()["data"]
    assert "composite_risk_score" in data
    assert data["risk_level"] in {"Very Low", "Low", "Moderate", "High", "Extreme"}

    r3 = client.post(
        "/api/v1/risk/apply-plan",
        json={
            "trading_plan": {"preferred_direction": "long", "session_notes": "", "confirmation_conditions": []},
            "risk_object": {
                "composite_risk_score": 90,
                "risk_level": "Extreme",
                "no_trade_zone": True,
                "suppressed": True,
                "suppression_log": ["extreme"],
                "exposure_fraction": 0.0,
                "suggested_exposure": "No new position",
                "capital_preservation_mode": "Lockdown",
                "explanation": "NTZ",
            },
        },
    )
    assert r3.status_code == 200
    assert r3.json()["data"]["preferred_direction"] == "no_trade"
