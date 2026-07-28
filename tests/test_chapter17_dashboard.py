"""Chapter 17 — Dashboard, Visualization & User Experience tests."""

from __future__ import annotations

from src.dashboard.builder import build_dashboard_view, status_catalog
from src.dashboard.cards import build_domain_cards
from src.dashboard.colors import bias_tone, risk_tone
from src.dashboard.contracts import DashboardState, Personalization
from src.dashboard.explain import build_explainability
from src.dashboard.hierarchy import NAVIGATION, PERFORMANCE_TARGETS
from src.dashboard.state import resolve_dashboard_state
from src.dashboard.engine import DashboardEngine


def test_bias_and_risk_tones():
    assert bias_tone("Strong Bullish") == "green"
    assert bias_tone("Bearish") == "red"
    assert bias_tone("Neutral") == "gray"
    assert risk_tone(90) == "red"
    assert risk_tone("Low") == "green"


def test_dashboard_states():
    assert resolve_dashboard_state(has_payload=False) == DashboardState.LOADING.value
    assert resolve_dashboard_state(has_payload=True, connection_ok=True) == DashboardState.LIVE.value
    assert resolve_dashboard_state(has_payload=False, connection_ok=False) == DashboardState.OFFLINE.value
    assert resolve_dashboard_state(has_payload=True, maintenance=True) == DashboardState.MAINTENANCE.value
    assert resolve_dashboard_state(has_payload=True, partial_services=True) == DashboardState.DEGRADED.value


def test_domain_cards_six_domains():
    cards = build_domain_cards(
        analysis={
            "market_bias": "Bullish",
            "market_regime": "Uptrend",
            "layer_results": [
                {"layer": "Spot", "summary": "spot ok", "details": {"price": 65000, "vwap": 64800}},
                {"layer": "Futures", "summary": "fut", "details": {"funding_rate": 0.01}},
                {"layer": "Options", "summary": "opt", "details": {"put_call_ratio": 0.8}},
                {"layer": "Liquidity", "summary": "liq", "details": {"sweep_probability": 0.2}},
                {"layer": "Volatility", "summary": "vol", "details": {"atr": 1200, "regime": "Normal"}},
                {"layer": "Market Structure", "summary": "ms", "details": {"bos": True}, "tags": ["BOS"]},
            ],
        },
        intelligence={"liquidity_state": "Balanced", "volatility_regime": "Normal"},
        snapshot={"mark_price": 65000},
    )
    ids = [c.id for c in cards]
    assert ids == ["spot", "futures", "options", "liquidity", "volatility", "structure"]
    assert cards[0].metrics[0].value == 65000


def test_explainability_includes_ntz():
    block = build_explainability(
        market_bias="Bullish",
        intelligence={"market_stress_index": "Low", "liquidity_state": "Balanced"},
        scoring={},
        risk={"no_trade_zone": True, "risk_level": "Extreme", "composite_risk_score": 90},
        reasoning={"supporting_evidence": ["Strong spot accumulation"]},
    )
    texts = [b["text"] for b in block.bullets]
    assert block.question == "Why Bullish?"
    assert any("No Trade Zone" in t for t in texts)
    assert any(b["ok"] for b in block.bullets)


def test_personalization_presentation_only():
    prefs = Personalization(theme="ops-dark", alert_min_severity="High", favorite_assets=["BTCUSDT", "ETHUSDT"])
    d = prefs.to_dict()
    assert d["theme"] == "ops-dark"
    roundtrip = Personalization.from_dict(d)
    assert roundtrip.alert_min_severity == "High"


def test_build_view_hierarchy_and_executive():
    view = build_dashboard_view(
        ai_report={
            "symbol": "BTCUSDT",
            "market_bias": "Bullish",
            "confidence": 82,
            "market_regime": "Strong Uptrend",
            "primary_narrative": "Institutional bid",
            "primary_scenario": "Bullish Continuation",
            "scenarios": [{"name": "Bullish Continuation", "probability": 55}],
            "alternative_scenarios": [{"name": "Sideways", "probability": 25}],
            "trading_plan": {"preferred_direction": "long", "position_sizing_guidance": "Moderate"},
            "reasoning": {"primary_conclusion": "Bullish with confirmation", "supporting_evidence": ["Spot accumulation"]},
            "analyzed_at": "2026-07-28T12:00:00Z",
        },
        intelligence={
            "market_regime": "Strong Uptrend",
            "market_health_index": "Healthy",
            "market_stress_index": "Low",
            "liquidity_state": "Balanced",
            "volatility_regime": "Normal",
        },
        scoring={"market_bias": "Bullish", "confidence_score": 82, "data_quality_score": 88},
        risk={"composite_risk_score": 32, "risk_level": "Low", "no_trade_zone": False, "explanation": "Contained"},
        events=[
            {"type": "Market Regime Change", "severity": "High", "summary": "Regime up", "category": "Trend", "asset": "BTCUSDT", "state": "Active"},
            {"type": "Noise", "severity": "Informational", "summary": "info", "category": "Trend", "suppressed": False},
        ],
        personalization=Personalization(alert_min_severity="Medium"),
        connection_ok=True,
    )
    d = view.to_dict()
    assert d["state"] == "Live"
    assert d["header"]["asset"] == "BTCUSDT"
    assert d["header"]["fixed"] is True
    assert d["executive"]["market_bias"] == "Bullish"
    assert d["executive"]["confidence_score"] == 82
    assert len(d["domain_cards"]) == 6
    assert "level_1_immediate_status" in d["levels"]
    assert d["levels"]["level_1_immediate_status"]["visible_without_scroll_desktop"] is True
    # Informational filtered out by min severity Medium
    assert d["alerts"]["active_count"] == 1
    assert d["explainability"]["question"] == "Why Bullish?"
    assert d["navigation"]["max_clicks_to_feature"] == 2


def test_navigation_and_performance_targets():
    assert NAVIGATION["max_clicks_to_feature"] == 2
    assert PERFORMANCE_TARGETS["initial_load_ms"] == 2000
    cat = status_catalog()
    assert "Observe" in cat["philosophy"]
    assert "Metric Card" in cat["component_library"]
    assert "keyboard_navigation" in cat["accessibility"]


def test_engine_preferences_roundtrip():
    eng = DashboardEngine()
    prefs = eng.set_preferences({"preferred_timeframe": "4h", "display_density": "compact"})
    assert prefs.preferred_timeframe == "4h"
    assert eng.get_preferences().display_density == "compact"


def test_dashboard_api():
    from fastapi.testclient import TestClient

    from src.api.app import app

    client = TestClient(app)
    r = client.get("/api/v1/dashboard/status")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["philosophy"] == ["Observe", "Understand", "Decide"]

    r2 = client.post(
        "/api/v1/dashboard/view",
        json={
            "use_cache": False,
            "ai_report": {
                "symbol": "BTCUSDT",
                "market_bias": "Bearish",
                "confidence": 60,
                "market_regime": "Downtrend",
                "scenarios": [{"name": "Bearish Reversal", "probability": 50}],
                "trading_plan": {"preferred_direction": "no_trade"},
                "analyzed_at": "2026-07-28T12:00:00Z",
            },
            "intelligence": {"market_stress_index": "Elevated", "market_regime": "Downtrend", "volatility_regime": "Elevated"},
            "scoring": {"market_bias": "Bearish", "confidence_score": 60, "data_quality_score": 75},
            "risk": {"composite_risk_score": 55, "risk_level": "Moderate"},
            "events": [],
        },
    )
    assert r2.status_code == 200
    view = r2.json()["data"]
    assert view["executive"]["market_bias"] == "Bearish"
    assert len(view["domain_cards"]) == 6

    r3 = client.post("/api/v1/dashboard/preferences", json={"theme": "ops-dark", "alert_min_severity": "High"})
    assert r3.status_code == 200
    assert r3.json()["data"]["alert_min_severity"] == "High"

    r4 = client.get("/api/v1/dashboard/view")
    assert r4.status_code == 200


def test_frontend_shell_exists():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "frontend"
    assert (root / "index.html").exists()
    assert (root / "dashboard.html").exists()
    index = (root / "index.html").read_text(encoding="utf-8")
    assert 'lang="fa"' in index
    assert "BTC Analyzer" in index
    assert "داشبورد" in index
    dash = (root / "dashboard.html").read_text(encoding="utf-8")
    assert "وضعیت بازار" in dash
    assert "مرکز هشدار" in dash
    assert (root / "css" / "fa.css").exists()
    assert (root / "css" / "style.css").exists()
    assert (root / "js" / "dashboard.js").exists()
    assert (root / "js" / "nav.js").exists()
    css = (root / "css" / "style.css").read_text(encoding="utf-8")
    assert "--green" in css and "--red" in css and "--amber" in css
    for page in ("guide.html", "setup.html", "ssl.html", "status.html", "admin.html"):
        assert (root / page).exists(), page
    assert "پنل مدیریت" in (root / "index.html").read_text(encoding="utf-8")
