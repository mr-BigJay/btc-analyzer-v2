# BTC Analyzer Enterprise Design Book
## Chapter 5 — System Infrastructure & Backend Architecture
**Version:** 1.0

> Canonical backend infrastructure specification. Source: Enterprise Design Book, Chapter 5.

---

### 5.1 Purpose

Modular FastAPI backend for real-time ingestion, scheduled processing, AI analysis, REST + WebSocket APIs, and future microservice migration.

### 5.2 Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12+ |
| Web | FastAPI + Uvicorn |
| DB / Cache | PostgreSQL + Redis |
| ORM / Migrations | SQLAlchemy + Alembic |
| Scheduler | APScheduler |
| Logging | Loguru |
| Containers | Docker + Nginx |

Celery / Prometheus / Grafana / JWT = future.

### 5.3 Package Mapping (`app/` → `src/`)

| Design Book | Implementation |
|-------------|----------------|
| `app/api` | `src/api/` |
| `app/collectors` | `src/collectors/` |
| `app/analysis` | `src/analysis/` |
| `app/ai` | `src/engine/` + `src/outlook/` |
| `app/decision` | `src/engine/` |
| `app/scheduler` | `src/scheduler/` |
| `app/websocket` | `src/websocket/` |
| `app/database` / `models` | `src/db/` |
| `app/services` | `src/services/` |
| `app/cache` | `src/cache/` + `src/storage/` |
| `app/config` | `src/config.py` |

### 5.4 Communication Flow

```
Collectors → Database → Analysis → AI → Decision → Dashboard/API
```

All persistence via Central Repository. No cross-module DB access.

### 5.5 API Principles

- Versioned `/api/v1`
- JSON only, UTC timestamps
- Request / correlation IDs
- Envelope: `{ status, timestamp, request_id, data }`
- Consistent error objects

### 5.6 Scheduler

| Interval | Task |
|----------|------|
| Realtime | WebSocket streams |
| 1 Minute | Funding, OI, trades |
| 5 Minutes | Technical indicators |
| 15 Minutes | Pattern detection |
| Hourly | Options metrics |
| Daily 03:30 UTC | Daily Outlook |

Failures are isolated per job.

### 5.7 Docker

`nginx` → `fastapi` · `scheduler` · `redis` · `postgres`
