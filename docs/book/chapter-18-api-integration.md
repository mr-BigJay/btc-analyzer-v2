# BTC Analyzer Enterprise Design Book
## Chapter 18 — API Specification & Integration Guide
**Version:** 1.0

> All external integrations communicate exclusively through published `/api/v1/` contracts. Business logic is never duplicated outside the core platform.

---

### 18.1 Purpose

Stable, versioned, secure, explainable API surface for dashboards, bots, mobile apps, and automation.

### 18.2 Envelope

Success: `{status, timestamp, request_id, data}`  
Error: `{status, timestamp, request_id, error:{code,message,details}}`

### 18.3 Package Mapping

| Spec | Code |
|------|------|
| Contracts / MI response | `src/api_spec/contracts.py`, `market_contract.py` |
| Auth / RBAC / JWT | `src/api_spec/auth.py`, `src/api/deps.py` |
| Validation / pagination | `src/api_spec/validation.py`, `pagination.py` |
| Idempotency / webhooks | `src/api_spec/idempotency.py`, `webhooks.py` |
| Observability / catalog | `src/api_spec/observability.py`, `catalog.py` |
| Public resources | `/api/v1/assets`, `/market/{symbol}`, `/reports/*`, `/alerts`, `/system/health` |
| Integration ops | `/api/v1/integration/*` |
| Thin Python SDK | `sdk/python/btc_analyzer_client.py` |

### 18.4 Auth

API Key (`X-API-Key`) · JWT Bearer · Refresh Token · Roles: Viewer / Analyst / Operator / Administrator

### 18.5 Compatibility

Fields never repurposed · optional fields may be added · breaking changes require `/api/v2/`
