"""Observability engine (Ch.21)."""

from __future__ import annotations

from typing import Any

from src.observability.alerts import alert_store, evaluate_alerts
from src.observability.anomaly import detect_anomalies
from src.observability.catalog import observability_catalog
from src.observability.dashboards import build_observability_object, capacity_snapshot, service_health_dashboard
from src.observability.logging_schema import structured_log_record
from src.observability.metrics import app_metrics
from src.observability.slo import evaluate_slos
from src.observability.tracing import trace_store


class ObservabilityEngine:
    def status(self) -> dict[str, Any]:
        return observability_catalog()

    def observability_object(self, service: str = "api") -> dict[str, Any]:
        return build_observability_object(service).to_dict()

    def metrics(self) -> dict[str, Any]:
        return app_metrics.snapshot()

    def slos(self) -> dict[str, Any]:
        return evaluate_slos()

    def alerts(self, *, evaluate: bool = True) -> dict[str, Any]:
        if evaluate:
            return evaluate_alerts()
        return {"active_alerts": alert_store.active_count(), "recent": alert_store.list(limit=50)}

    def traces(
        self,
        *,
        limit: int = 50,
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        rows = trace_store.list(limit=limit, trace_id=trace_id, correlation_id=correlation_id)
        return {"traces": rows, "count": len(rows)}

    def dashboard(self) -> dict[str, Any]:
        return service_health_dashboard()

    def anomalies(self) -> dict[str, Any]:
        return detect_anomalies()

    def capacity(self) -> dict[str, Any]:
        return capacity_snapshot()

    def log_example(self, **kwargs: Any) -> dict[str, Any]:
        return structured_log_record(**kwargs)
