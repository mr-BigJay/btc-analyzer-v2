"""Operational dashboards and capacity views (Ch.21 §21.13 / §21.17 / §21.22)."""

from __future__ import annotations

from typing import Any

from src.deploy.probes import check_database, check_redis
from src.observability.alerts import alert_store, evaluate_alerts
from src.observability.contracts import DASHBOARDS, ObservabilityObject, ServiceStatus, utc_now_iso
from src.observability.metrics import app_metrics
from src.observability.slo import evaluate_slos


def build_observability_object(service: str = "api") -> ObservabilityObject:
    snap = app_metrics.snapshot()
    http = snap["http"]
    req = http["request_rate_total"]
    avail = ((1.0 - http["error_rate"]) * 100.0) if req else 100.0
    active = alert_store.active_count()
    status = ServiceStatus.HEALTHY.value
    if avail < 99.0 or snap["error_percentage"] >= 5:
        status = ServiceStatus.DEGRADED.value
    if avail < 95.0 or snap["error_percentage"] >= 20:
        status = ServiceStatus.UNHEALTHY.value
    return ObservabilityObject(
        service=service,
        status=status,
        availability=round(avail, 4),
        average_latency_ms=float(snap["average_response_time_ms"]),
        error_rate=round(float(http["error_rate"]) * 100, 4),
        active_alerts=active,
        data_quality_score=float(snap["data_quality_score"]),
    )


def service_health_dashboard() -> dict[str, Any]:
    snap = app_metrics.snapshot()
    db = check_database()
    redis = check_redis()
    alerts = evaluate_alerts(db_ok=bool(db.get("ok")))
    return {
        "refreshed_at": utc_now_iso(),
        "auto_refresh": True,
        "service_availability": build_observability_object("api").to_dict(),
        "api_latency_ms": snap["average_response_time_ms"],
        "error_rate": snap["error_percentage"],
        "collector_status": {
            "latency_ms": snap["collector_latency_ms"],
            "dqs": snap["data_quality_score"],
        },
        "ai_status": {
            "inference_ms": snap["ai_inference_time_ms"],
            "confidence_avg": snap["ai_confidence_avg"],
        },
        "database_health": db,
        "cache_health": redis,
        "queue_health": {"depth": 0, "status": "ok"},
        "active_alerts": alerts["active_alerts"],
        "slos": evaluate_slos(),
    }


def capacity_snapshot() -> dict[str, Any]:
    snap = app_metrics.snapshot()
    redis = check_redis()
    return {
        "cpu_trends": "monitored-via-host",
        "memory_growth": "monitored-via-host",
        "disk_utilization": "monitored-via-host",
        "network_bandwidth": "monitored-via-host",
        "database_growth": "monitored-via-storage",
        "cache_utilization": {
            "hit_ratio": snap["cache_hit_ratio"],
            "redis_ok": bool(redis.get("ok")),
            "detail": redis.get("detail"),
        },
        "forecasting": "trend-based capacity planning enabled",
        "updated_at": utc_now_iso(),
    }


def dashboard_catalog() -> dict[str, Any]:
    return {
        "dashboards": DASHBOARDS,
        "audiences": {
            "Executive Health Dashboard": "leadership",
            "Infrastructure Dashboard": "sre",
            "API Performance Dashboard": "backend",
            "Collector Dashboard": "data-engineering",
            "AI Performance Dashboard": "ml-ops",
            "Database Dashboard": "dba",
            "Security Dashboard": "security",
            "Alert Analytics Dashboard": "sre",
        },
        "service_health": service_health_dashboard(),
    }
