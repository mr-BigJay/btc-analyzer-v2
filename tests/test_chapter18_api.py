"""Chapter 18 — API Specification & Integration tests."""

from __future__ import annotations

from src.api_spec.auth import authenticate_headers, issue_jwt, parse_api_keys, verify_jwt
from src.api_spec.catalog import api_catalog
from src.api_spec.contracts import MarketIntelligenceResponse
from src.api_spec.idempotency import lookup, store
from src.api_spec.market_contract import build_market_intelligence_response
from src.api_spec.pagination import filter_items, paginate, sort_items
from src.api_spec.validation import validate_query_params, validate_symbol
from src.api_spec.webhooks import WebhookRegistry, webhook_registry
from src.config import settings


def test_api_catalog_has_base_path_and_endpoints():
    cat = api_catalog()
    assert cat["base_path"] == "/api/v1/"
    assert cat["compatibility_policy"]["breaking_changes_require_major_version"] is True
    paths = {e["path"] for e in cat["endpoints"]}
    assert "/api/v1/assets" in paths
    assert "/api/v1/market/{symbol}" in paths


def test_symbol_validation():
    ok, err = validate_symbol("BTCUSDT")
    assert ok and err is None
    ok, err = validate_symbol("NOTREAL")
    assert not ok
    assert "not supported" in (err or "").lower() or "Invalid" in (err or "")


def test_jwt_roundtrip():
    token = issue_jwt(subject="tester", role="Analyst")
    payload = verify_jwt(token)
    assert payload is not None
    assert payload["sub"] == "tester"
    assert payload["role"] == "Analyst"
    assert verify_jwt("not.a.jwt") is None


def test_authenticate_api_key(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", "devkey123:Operator")
    # clear cache by re-parsing
    keys = parse_api_keys()
    assert keys["devkey123"] == "Operator"
    principal = authenticate_headers({"X-API-Key": "devkey123"})
    assert principal is not None
    assert principal.role == "Operator"
    assert authenticate_headers({"X-API-Key": "bad"}) is None


def test_paginate_sort_filter():
    rows = [{"timestamp": f"t{i}", "severity": "High" if i % 2 == 0 else "Low", "asset": "BTCUSDT"} for i in range(5)]
    filtered = filter_items(rows, severity="High", asset="BTCUSDT")
    assert len(filtered) == 3
    sorted_rows = sort_items(filtered, sort="timestamp", order="asc")
    assert sorted_rows[0]["timestamp"] == "t0"
    page, meta = paginate(sorted_rows, page=1, page_size=2)
    assert len(page) == 2
    assert meta.total_items == 3
    assert meta.total_pages == 2


def test_idempotency_store_lookup():
    store("abc-1", route="POST /test", response={"ok": True}, status_code=201)
    hit = lookup("abc-1", route="POST /test")
    assert hit is not None
    assert hit["body"]["ok"] is True
    assert lookup("missing", route="POST /test") is None


def test_webhook_sign_and_subscribe():
    reg = WebhookRegistry()
    # isolate by writing to redis via subscribe then list
    sub = reg.subscribe(url="https://example.com/hook", events=["Alert Created"], secret="s3cret")
    assert sub.subscription_id
    assert "Alert Created" in sub.events
    sig = reg.sign_payload({"a": 1}, "s3cret")
    assert isinstance(sig, str) and len(sig) == 64
    deliveries = reg.deliver("Alert Created", {"x": 1}, dry_run=True)
    assert deliveries
    assert deliveries[0]["dry_run"] is True
    assert deliveries[0]["signature"]


def test_canonical_market_intelligence_response():
    mi = build_market_intelligence_response(
        symbol="BTCUSDT",
        ai_report={
            "market_bias": "Bullish",
            "confidence": 86,
            "market_regime": "Strong Uptrend",
            "primary_scenario": "Bullish Continuation",
            "analyzed_at": "2026-07-28T12:00:00Z",
        },
        intelligence={"market_health_index": "Healthy", "market_stress_index": "Low", "market_regime": "Strong Uptrend"},
        scoring={"market_bias": "Bullish", "confidence_score": 86, "risk_score": 32},
        risk={"composite_risk_score": 32},
    )
    d = mi.to_dict()
    assert d["asset"] == "BTCUSDT"
    assert d["confidence_score"] == 86
    assert d["risk_score"] == 32
    assert d["schema_version"] == "1.0"
    assert set(d) >= {
        "asset",
        "market_bias",
        "market_regime",
        "confidence_score",
        "risk_score",
        "market_health_index",
        "market_stress_index",
        "primary_scenario",
        "last_updated",
        "schema_version",
    }


def test_validate_query_params():
    errs = validate_query_params({"symbol": "BTCUSDT", "from": "2026-07-01T00:00:00Z", "limit": 10})
    assert errs == []
    errs = validate_query_params({"symbol": "BAD", "limit": 9999})
    assert errs


def test_integration_api_endpoints():
    from fastapi.testclient import TestClient

    from src.api.app import app

    client = TestClient(app)
    r = client.get("/api/v1/integration/status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert "request_id" in body
    assert body["data"]["base_path"] == "/api/v1/"

    r2 = client.get("/api/v1/assets")
    assert r2.status_code == 200
    assert "BTCUSDT" in [a["symbol"] for a in r2.json()["data"]["assets"]]

    r3 = client.get("/api/v1/assets/FAKECOIN")
    assert r3.status_code == 404
    assert r3.json()["error"]["code"] == "INVALID_SYMBOL"

    r4 = client.get("/api/v1/market/BTCUSDT")
    assert r4.status_code == 200
    mi = r4.json()["data"]
    assert mi["asset"] == "BTCUSDT"
    assert "confidence_score" in mi

    r5 = client.get("/api/v1/alerts?page=1&page_size=10")
    assert r5.status_code == 200
    assert "pagination" in r5.json()["data"]

    r6 = client.get("/api/v1/system/health")
    assert r6.status_code == 200
    assert r6.json()["data"]["chapter"] == "23-governance-roadmap"

    r7 = client.post("/api/v1/integration/auth/token", json={"subject": "ci", "role": "Analyst"})
    assert r7.status_code == 201
    token = r7.json()["data"]["access_token"]
    assert token

    r8 = client.post(
        "/api/v1/integration/webhooks",
        headers={"Idempotency-Key": "hook-1"},
        json={"url": "https://example.com/h", "events": ["Alert Created"]},
    )
    assert r8.status_code == 201
    r8b = client.post(
        "/api/v1/integration/webhooks",
        headers={"Idempotency-Key": "hook-1"},
        json={"url": "https://example.com/h", "events": ["Alert Created"]},
    )
    assert r8b.status_code == 200 or r8b.status_code == 201
    assert r8b.json()["data"]["subscription_id"] == r8.json()["data"]["subscription_id"]

    r9 = client.get("/api/v1/integration/metrics")
    assert r9.status_code == 200
    assert "request_rate_total" in r9.json()["data"]

    r10 = client.get("/api/openapi.json")
    assert r10.status_code == 200
    assert "ApiKeyAuth" in r10.json()["components"]["securitySchemes"]


def test_sdk_client_importable():
    from sdk.python.btc_analyzer_client import BtcAnalyzerClient

    c = BtcAnalyzerClient(base_url="http://example.invalid")
    assert c.base_url == "http://example.invalid"
