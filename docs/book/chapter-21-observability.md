# BTC Analyzer Enterprise Design Book
## Chapter 21 — Monitoring, Logging & Observability
**Version:** 1.0

> Observability is designed into the platform: metrics, structured logs, and traces with SLOs and actionable alerts.

---

### 21.1 Objectives

End-to-end visibility · Centralized monitoring · Structured logging · Distributed tracing · Performance analytics · Capacity monitoring · Anomaly detection · Actionable alerting

### 21.2 Package Mapping

| Spec | Code |
|------|------|
| Observability Object / SLOs / retention | `src/observability/contracts.py` |
| Metrics store | `src/observability/metrics.py` (+ `src/api_spec/observability.py`) |
| Structured logs | `src/observability/logging_schema.py`, `src/logging_setup.py` |
| Distributed tracing | `src/observability/tracing.py` (middleware root span) |
| SLI / SLO / error budget | `src/observability/slo.py` |
| Alert rules | `src/observability/alerts.py` |
| Anomaly detection | `src/observability/anomaly.py` |
| Dashboards / capacity | `src/observability/dashboards.py` |
| Engine / service / API | `src/observability/engine.py`, `src/services/observability.py`, `/api/v1/observability/*` |

### 21.3 Pillars

Metrics · Logs · Traces

### 21.4 Standard Observability Object

service · status · availability · average_latency_ms · error_rate · active_alerts · data_quality_score · schema_version `1.0`

### 21.5 SLOs

API ≥ 99.9% · Collectors ≥ 99.95% · Dashboard ≥ 99.9% · Avg latency < 250 ms · Freshness < 5 s

### 21.6 Correlation

`X-Request-ID` / correlation ID preserved across components; `X-Trace-ID` on responses.
