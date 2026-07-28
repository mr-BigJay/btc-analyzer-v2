# BTC Analyzer Enterprise Design Book
## Chapter 20 — Deployment, DevOps & Infrastructure
**Version:** 1.0

> Reproducible, portable, and reversible deployments with health-gated releases.

---

### 20.1 Objectives

Reproducible deployments · Environment consistency · Minimal downtime · Automated rollback · Horizontal scale · Portability · Resilience

### 20.2 Package Mapping

| Spec | Code |
|------|------|
| Deployment Object / contracts | `src/deploy/contracts.py` |
| Environments / env validation | `src/deploy/environments.py` |
| Health / ready / live probes | `src/deploy/probes.py`, `src/api/routers/health.py` |
| Production checklist / rollback | `src/deploy/readiness.py` |
| Catalog / engine / service | `src/deploy/catalog.py`, `engine.py`, `src/services/deploy.py` |
| API | `/api/v1/deploy/*` |
| Compose topology | `docker-compose.yml` |
| Reverse proxy + probes | `deploy/nginx.conf` |
| Backup helper | `deploy/scripts/backup.sh` |
| CI pipeline | `.github/workflows/ci.yml` |
| Ops helpers | `Makefile`, `deploy/README.md` |

### 20.3 Standard Deployment Object

Environment · application_version · Blue-Green · Docker · PostgreSQL · Redis · monitoring · rollback_enabled · schema_version `1.0`

### 20.4 Probes

`/health` · `/ready` · `/live` (+ `/api/v1/*` aliases)

### 20.5 Production Checklist

Tests · Security scan · Migrations · Health · Backup · Rollback · Monitoring · Logging · Env validation

### 20.6 DR Targets

RTO ≤ 30 minutes · RPO ≤ 5 minutes
