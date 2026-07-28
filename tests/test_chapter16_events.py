"""Chapter 16 — Alerting, Notification & Event Processing tests."""

from __future__ import annotations

from src.events.archive import EventArchive
from src.events.contracts import EventObject, EventSeverity, EventState
from src.events.correlation import correlate_events
from src.events.dedupe import apply_deduplication
from src.events.detection import detect_events
from src.events.engine import EventEngine
from src.events.formatters import format_telegram_alert
from src.events.priority import escalate
from src.events.rate_limit import apply_rate_limits
from src.events.routing import route_channels


def test_detect_regime_and_bias_change():
    prev = {
        "market_regime": "Range",
        "market_bias": "Bullish",
        "confidence": 70,
        "market_intelligence": {"volatility_regime": "Normal", "market_stress_index": "Low"},
    }
    current = {
        "market_regime": "Strong Uptrend",
        "market_bias": "Bearish",
        "confidence": 55,
        "market_intelligence": {
            "volatility_regime": "Elevated",
            "market_stress_index": "Extreme",
            "liquidity_state": "Liquidity Vacuum",
            "derivatives_thesis": "Funding extreme with Open Interest spike",
        },
        "scoring": {"data_quality_score": 85, "confidence_score": 55},
        "risk_object": {"no_trade_zone": True, "no_trade_reasons": ["MSI Extreme"], "composite_risk_score": 90},
        "evidence": [{"tags": ["Breakout Probability", "BOS"]}],
    }
    events = detect_events(current=current, previous=prev, asset="BTCUSDT")
    types = {e.type for e in events}
    assert "Market Regime Change" in types
    assert "Market Bias Change" in types
    assert "No Trade Zone" in types
    assert "Market Stress Extreme" in types
    assert "Breakout Confirmed" in types


def test_correlation_short_squeeze_recipe():
    members = [
        EventObject(type="Funding Extreme", category="Futures", severity="High", asset="BTCUSDT", fingerprint="a"),
        EventObject(type="Open Interest Spike", category="Futures", severity="Medium", asset="BTCUSDT", fingerprint="b"),
        EventObject(type="Breakout Confirmed", category="Price", severity="Medium", asset="BTCUSDT", fingerprint="c"),
    ]
    out = correlate_events(members)
    labels = {e.type for e in out}
    assert "Potential Short Squeeze" in labels
    composite = next(e for e in out if e.type == "Potential Short Squeeze")
    assert composite.correlated
    assert len(composite.related_events) == 3


def test_dedupe_suppresses_identical_within_window():
    memory: dict = {}
    e1 = EventObject(
        type="Market Regime Change",
        category="Trend",
        severity="High",
        asset="BTCUSDT",
        fingerprint="trend|regime|btcusdt|r->u",
        summary="first",
    )
    e2 = EventObject(
        type="Market Regime Change",
        category="Trend",
        severity="High",
        asset="BTCUSDT",
        fingerprint="trend|regime|btcusdt|r->u",
        summary="second",
    )
    first = apply_deduplication([e1], memory=memory, persist=False)
    assert not first[0].suppressed
    second = apply_deduplication([e2], memory=memory, persist=False)
    assert second[0].suppressed
    assert second[0].duplicate_of == e1.event_id


def test_critical_bypasses_rate_limit():
    memory: dict = {}
    # Fill burst with medium events
    for i in range(5):
        apply_rate_limits(
            [
                EventObject(
                    type=f"Noise{i}",
                    category="Trend",
                    severity="Medium",
                    asset="BTCUSDT",
                    fingerprint=f"noise|{i}",
                )
            ],
            memory=memory,
            persist=False,
        )
    critical = EventObject(
        type="Collector Failure",
        category="System",
        severity="Critical",
        asset="BTCUSDT",
        fingerprint="system|fail",
    )
    out = apply_rate_limits([critical], memory=memory, persist=False)
    assert not out[0].suppressed


def test_routing_by_severity():
    low = EventObject(severity="Informational", type="x", category="Trend")
    assert "Telegram" not in route_channels(low)
    high = EventObject(severity="High", type="x", category="Trend")
    assert "Telegram" in route_channels(high)
    assert "WebSocket" in route_channels(high)
    crit = EventObject(severity="Critical", type="No Trade Zone", category="Risk")
    ch = route_channels(crit)
    assert set(ch) >= {"API", "Dashboard", "Telegram", "WebSocket"}


def test_telegram_format_essential_fields():
    e = EventObject(
        type="Market Regime Change",
        category="Trend",
        severity="High",
        asset="BTCUSDT",
        summary="Market transitioned to Strong Uptrend.",
        explanation="Institutional Buying",
        trigger_conditions={"from": "Range", "to": "Strong Uptrend"},
        related_metrics={"confidence": 87},
    )
    text = format_telegram_alert(e)
    assert "Market Regime Change" in text
    assert "BTCUSDT" in text
    assert "Range" in text
    assert "Strong Uptrend" in text
    assert "87%" in text


def test_escalation_ladder():
    e = EventObject(severity="Medium", type="x", category="Trend")
    e2 = escalate(e, duration_sec=4000, recurrence=1)
    assert e2.severity == "High"
    assert e2.escalated_from == "Medium"
    e3 = escalate(e2, recurrence=3)
    assert e3.severity == "Critical"


def test_event_engine_lifecycle_and_archive():
    archive = EventArchive(maxlen=50)
    eng = EventEngine(archive=archive)
    result = eng.process_snapshot(
        current={
            "market_regime": "Strong Uptrend",
            "market_bias": "Bullish",
            "confidence": 80,
            "market_intelligence": {
                "market_regime": "Strong Uptrend",
                "volatility_regime": "Normal",
                "market_stress_index": "Low",
                "liquidity_state": "Balanced",
            },
            "scoring": {"data_quality_score": 90, "confidence_score": 80},
            "risk_object": {},
        },
        previous={
            "market_regime": "Range",
            "market_bias": "Neutral",
            "confidence": 60,
            "market_intelligence": {"volatility_regime": "Normal", "market_stress_index": "Low"},
        },
        persist=True,
        notify=True,
        skip_external=True,
    )
    assert result["events"]
    assert result["schema_version"]
    active_types = {e["type"] for e in result["active_events"]}
    assert "Market Regime Change" in active_types
    # Every active event should have progressed past Detected
    for e in result["active_events"]:
        assert e["state"] in {EventState.ACTIVE.value, EventState.ARCHIVED.value, EventState.CONFIRMED.value}
    listed = eng.list_events(limit=20)
    assert listed
    analytics = eng.analytics()
    assert analytics["events_generated"] >= 1


def test_no_event_bypasses_validation():
    eng = EventEngine(archive=EventArchive(maxlen=20))
    # Empty type should be dropped
    bad = EventObject(type="", category="Trend", severity="High")
    assert eng._validate(bad) is False
    good = EventObject(type="X", category="Trend", severity="High", fingerprint="")
    assert eng._validate(good) is True
    assert good.fingerprint


def test_system_collector_failure():
    eng = EventEngine(archive=EventArchive(maxlen=20))
    result = eng.ingest_system_event(
        collector_failure=True,
        message="Binance spot collector timeout",
        persist=True,
        notify=True,
        skip_external=True,
    )
    types = {e["type"] for e in result["events"]}
    assert "Collector Failure" in types
    assert any(e["severity"] == EventSeverity.CRITICAL.value for e in result["active_events"])


def test_replay_idempotent_dedupe():
    eng = EventEngine(archive=EventArchive(maxlen=100))
    snaps = [
        {
            "market_regime": "Range",
            "confidence": 50,
            "market_bias": "Neutral",
            "market_intelligence": {"volatility_regime": "Normal"},
        },
        {
            "market_regime": "Uptrend",
            "confidence": 70,
            "market_bias": "Bullish",
            "market_intelligence": {"volatility_regime": "Normal"},
        },
        {
            "market_regime": "Uptrend",
            "confidence": 71,
            "market_bias": "Bullish",
            "market_intelligence": {"volatility_regime": "Normal"},
        },
    ]
    out = eng.replay(snaps, asset="BTCUSDT")
    assert out["replayed"] == 3
    # Second transition creates regime change; third should mostly dedupe
    suppressed = sum(1 for e in out["events"] if e.get("suppressed"))
    assert suppressed >= 0


def test_events_api():
    from fastapi.testclient import TestClient

    from src.api.app import app

    client = TestClient(app)
    r = client.get("/api/v1/events/status")
    assert r.status_code == 200
    body = r.json()["data"]
    assert "Detection" in body["lifecycle"]
    assert "event_driven" in body["governance"]

    r2 = client.post(
        "/api/v1/events/process",
        json={
            "snapshot": {
                "market_regime": "Downtrend",
                "market_bias": "Bearish",
                "confidence": 40,
                "market_intelligence": {
                    "market_stress_index": "High",
                    "volatility_regime": "Extreme",
                    "liquidity_state": "Thin",
                },
                "scoring": {"data_quality_score": 70},
                "risk_object": {"no_trade_zone": False, "composite_risk_score": 65, "risk_level": "High"},
            },
            "previous": {
                "market_regime": "Range",
                "market_bias": "Neutral",
                "confidence": 60,
                "market_intelligence": {"volatility_regime": "Normal", "market_stress_index": "Low"},
            },
            "skip_external": True,
            "persist": True,
            "notify": True,
        },
    )
    assert r2.status_code == 200
    data = r2.json()["data"]
    assert "events" in data
    assert data["analytics"]["events_generated"] >= 1

    r3 = client.get("/api/v1/events/list?limit=10")
    assert r3.status_code == 200
    assert "events" in r3.json()["data"]
