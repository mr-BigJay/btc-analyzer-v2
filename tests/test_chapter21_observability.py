"""Chapter 21 — Monitoring, Logging & Observability tests."""

from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("/tmp/btc_analyzer_ch21_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["REDIS_URL"] = ""
os.environ["APP_ENV"] = "testing"
os.environ["API_RATE_LIMIT_PER_MINUTE"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402

from src.api.app import app  # noqa: E402
from src.db.session import init_db, reset_engine  # noqa: E402
from src.observability.alerts import alert_store, evaluate_alerts
from src.observability.anomaly import detect_anomalies
from src.observability.contracts import ObservabilityObject, ServiceStatus
from src.observability.logging_schema import structured_log_record
from src.observability.metrics import app_metrics
from src.observability.slo import evaluate_slos
from src.observability.tracing import traced, trace_store
from src.services.observability import ObservabilityService


def setup_module():
    reset_engine()
    init_db(seed=True)
    alert_store.clear()
    trace_store.clear()


def test_observability_object_shape():
    obj = ObservabilityObject(service="analysis", status=ServiceStatus.HEALTHY.value, availability=99.97)
    d = obj.to_dict()
    assert d["service"] == "analysis"
    assert d["status"] == "Healthy"
    assert d["availability"] == 99.97
    assert d["schema_version"] == "1.0"
    assert "last_updated" in d


def test_structured_log_schema():
    rec = structured_log_record(
        message="Trend analysis completed.",
        service="analysis",
        module="market_structure",
        request_id="uuid-test",
        duration_ms=43,
    )
    assert rec["level"] == "INFO"
    assert rec["service"] == "analysis"
    assert rec["module"] == "market_structure"
    assert rec["request_id"] == "uuid-test"
    assert rec["duration_ms"] == 43
    assert "timestamp" in rec


def test_tracing_context_manager():
    with traced("market.analysis", service="analysis", attributes={"symbol": "BTCUSDT"}) as span:
        assert span.span_id
        assert span.trace_id
        with traced("ai.inference", service="ai") as child:
            assert child.parent_span_id == span.span_id
            assert child.trace_id == span.trace_id
    rows = trace_store.list(limit=10)
    names = {r["name"] for r in rows}
    assert "market.analysis" in names
    assert "ai.inference" in names


def test_metrics_and_slos():
    app_metrics.record_cache(hit=True)
    app_metrics.record_cache(hit=False)
    app_metrics.record_ai(inference_ms=12.5, confidence=72.0)
    app_metrics.record_collector(80.0)
    app_metrics.record_dqs(98.0)
    snap = app_metrics.snapshot()
    assert snap["cache_hit_ratio"] == 0.5
    assert snap["ai_inference_time_ms"] == 12.5
    assert snap["data_quality_score"] == 98.0
    slo = evaluate_slos()
    assert "slos" in slo
    assert slo["error_budget_example"]["allowed_failure_budget"] == "0.1%"
    keys = {r["key"] for r in slo["slos"]}
    assert "api_availability" in keys
    assert "avg_api_latency_ms" in keys


def test_alerts_and_anomalies():
    alert_store.clear()
    out = evaluate_alerts(db_ok=True)
    assert "conditions" in out
    assert "Service unavailable" in out["conditions"]
    # Force anomaly thresholds
    for _ in range(5):
        app_metrics.record_collector(600.0)
    anom = detect_anomalies()
    assert anom["count"] >= 1
    assert any(f["type"] == "Collector slowdown" for f in anom["findings"])


def test_observability_service_and_api():
    client = TestClient(app)
    status = ObservabilityService().status()
    assert status["schema_version"] == "1.0"
    assert "Metrics" in status["pillars"]
    assert status["observability_object"]["schema_version"] == "1.0"

    r = client.get("/api/v1/observability/status")
    assert r.status_code == 200
    assert r.json()["data"]["engine_version"] == "1.0"
    assert r.headers.get("X-Trace-ID")

    r2 = client.get("/api/v1/observability/object")
    assert r2.status_code == 200
    assert r2.json()["data"]["service"] == "api"

    r3 = client.get("/api/v1/observability/metrics")
    assert r3.status_code == 200
    assert "requests_per_second" in r3.json()["data"]

    r4 = client.get("/api/v1/observability/slos")
    assert r4.status_code == 200
    assert r4.json()["data"]["slos"]

    r5 = client.get("/api/v1/observability/alerts")
    assert r5.status_code == 200

    r6 = client.get("/api/v1/observability/traces")
    assert r6.status_code == 200
    assert r6.json()["data"]["count"] >= 1

    r7 = client.get("/api/v1/observability/dashboard")
    assert r7.status_code == 200
    assert r7.json()["data"]["auto_refresh"] is True

    r8 = client.get("/api/v1/observability/anomalies")
    assert r8.status_code == 200

    r9 = client.get("/api/v1/observability/capacity")
    assert r9.status_code == 200

    health = client.get("/api/v1/health").json()["data"]
    assert health["chapter"] == "23-governance-roadmap"
    assert health["phase"] == "rewrite-ch23"

    arch = client.get("/api/v1/architecture").json()["data"]
    assert arch["observability"]["chapter"] == 21
    assert arch["observability"]["pillars"] == ["Metrics", "Logs", "Traces"]
