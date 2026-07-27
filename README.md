# BTC Analyzer v3

Professional AI-powered **crypto market intelligence** platform.
**Decision Support System (DSS)** — evidence-based scenarios, not guaranteed direction.

> Enterprise Design Book is the source of truth.

## Core Principles

**Ch.1–2:** DSS · Modular architecture · Standardized `ModuleResult`  
**Ch.3:** Collect ≠ Analyze · Retry/cache fallback · Isolated collectors  
**Ch.4:** Database is SSOT · PostgreSQL + Redis · FK integrity · Alembic  
**Ch.6:** 8 evidence layers · weighted scoring · conflict resolution · scenarios  
**Ch.7:** AI Decision Engine · narratives · calibrated confidence · Daily Outlook / Trading Plan

## Analysis → AI Pipeline

```
Analysis Engine (8 layers)
        ↓
 AI Decision Engine (evidence → narrative → probabilities → risk → NLG)
        ↓
 Daily Outlook + Intraday Trading Plan
```

API:  
`GET /api/v1/market/analysis` · `/decision` · `/outlook` · `/trading-plan`  
CLI: `python -m src.main analyze` · `python -m src.main outlook`

## Design Book

| Chapter | Topic | Status |
|---------|--------|--------|
| 01–06 | Intro → Analysis Engine | ✅ |
| 07 | AI Decision Engine | ✅ |
| 08 | Presentation / UX | Pending |

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
python -m src.main init-db
python -m src.main serve     # API :8000  ·  /api/docs  ·  /ws
python -m src.main run       # scheduler
python -m src.main outlook   # AI Daily Outlook once
```

### Docker (Nginx + API + Scheduler + Postgres + Redis)

```bash
docker compose up -d
# http://localhost/api/v1/health
```

## Status

Rewrite in progress. Chapters 1–7 applied. Awaiting Chapter 8 (Presentation).
