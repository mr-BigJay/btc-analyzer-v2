# BTC Analyzer v3

Professional AI-powered **crypto market intelligence** platform.
**Decision Support System (DSS)** — evidence-based scenarios, not guaranteed direction.

> Enterprise Design Book is the source of truth.

## Core Principles

**Ch.1–2:** DSS · Modular architecture · Standardized `ModuleResult`  
**Ch.3:** Collect ≠ Analyze · Retry/cache fallback · Isolated collectors  
**Ch.4:** Database is SSOT · PostgreSQL + Redis · FK integrity · Alembic  
**Ch.5:** FastAPI services · Loguru · Nginx · WebSocket · Versioned `/api/v1` envelopes

## Backend (Ch.5)

```
Nginx → FastAPI (REST + WebSocket)
          ├─ Collection Service
          ├─ Analysis Service
          ├─ Market Service
          └─ Scheduler (separate process)
PostgreSQL · Redis
```

**Scheduler:** realtime WS · 1m funding/OI · 5m technical · **15m patterns** · 1h options · daily 03:30 UTC  

**API envelope:**
```json
{ "status": "success", "timestamp": "…Z", "request_id": "…", "data": {} }
```

## Design Book

| Chapter | Topic | Status |
|---------|--------|--------|
| 01 | Introduction | ✅ |
| 02 | System Architecture | ✅ |
| 03 | Data Collection Engine | ✅ |
| 04 | Database Design | ✅ |
| 05 | Backend Architecture | ✅ |
| 06–08 | … | Pending |

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
python -m src.main init-db
python -m src.main serve     # API :8000  ·  /api/docs  ·  /ws
python -m src.main run       # scheduler
```

### Docker (Nginx + API + Scheduler + Postgres + Redis)

```bash
docker compose up -d
# http://localhost/api/v1/health
```

## Status

Rewrite in progress. Chapters 1–5 applied. Awaiting Chapters 6–8.
