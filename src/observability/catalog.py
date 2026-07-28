"""Observability catalog (Ch.21)."""

from __future__ import annotations

from typing import Any

from src.observability.alerts import evaluate_alerts
from src.observability.anomaly import detect_anomalies
from src.observability.contracts import (
    AI_METRICS,
    APPLICATION_METRICS,
    DASHBOARDS,
    MARKET_METRICS,
    OBSERVABILITY_ENGINE_VERSION,
    OBSERVABILITY_SCHEMA_VERSION,
    RETENTION,
)
from src.observability.dashboards import build_observability_object, capacity_snapshot, service_health_dashboard
from src.observability.logging_schema import LOG_LEVELS, structured_log_record
from src.observability.metrics import app_metrics
from src.observability.slo import evaluate_slos
from src.observability.tracing import TRACKED_OPERATIONS, trace_store


def observability_catalog() -> dict[str, Any]:
    return {
        "schema_version": OBSERVABILITY_SCHEMA_VERSION,
        "engine_version": OBSERVABILITY_ENGINE_VERSION,
        "pillars": {
            "Metrics": "Quantitative monitoring",
            "Logs": "Event history",
            "Traces": "Request lifecycle",
        },
        "objectives": [
            "End-to-end visibility",
            "Centralized monitoring",
            "Structured logging",
            "Distributed tracing",
            "Performance analytics",
            "Capacity monitoring",
            "Automated anomaly detection",
            "Actionable alerting",
        ],
        "application_metrics": APPLICATION_METRICS,
        "market_metrics": MARKET_METRICS,
        "ai_metrics": AI_METRICS,
        "log_levels": LOG_LEVELS,
        "structured_log_example": structured_log_record(
            message="Trend analysis completed.",
            service="analysis",
            module="market_structure",
            duration_ms=43,
        ),
        "tracked_operations": TRACKED_OPERATIONS,
        "dashboards": DASHBOARDS,
        "retention": RETENTION,
        "observability_object": build_observability_object().to_dict(),
        "metrics_snapshot": app_metrics.snapshot(),
        "slos": evaluate_slos(),
        "alerts": evaluate_alerts(),
        "anomalies": detect_anomalies(),
        "capacity": capacity_snapshot(),
        "service_health": service_health_dashboard(),
        "trace_count": len(trace_store.list(limit=2000)),
        "principles": [
            "Observe everything",
            "Correlate across services",
            "Prefer structured over unstructured data",
            "Detect problems before users do",
            "Measure against defined objectives",
            "Preserve operational history",
            "Use observability to continuously improve reliability",
        ],
        "endpoints": [
            "/api/v1/observability/status",
            "/api/v1/observability/object",
            "/api/v1/observability/metrics",
            "/api/v1/observability/slos",
            "/api/v1/observability/alerts",
            "/api/v1/observability/traces",
            "/api/v1/observability/dashboard",
            "/api/v1/observability/anomalies",
        ],
    }
