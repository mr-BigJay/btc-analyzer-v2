# BTC Analyzer v3

Professional AI-powered **crypto market intelligence** platform.
**Decision Support System (DSS)** — evidence-based scenarios, not guaranteed direction.

> Enterprise Design Book is the source of truth.

## Core Principles

**Ch.1–2:** DSS · Modular architecture · Standardized `ModuleResult`  
**Ch.3:** Collect ≠ Analyze · Retry/cache fallback · Isolated collectors  
**Ch.4:** Database is SSOT · PostgreSQL + Redis · FK integrity · Alembic  
**Ch.6:** 8 evidence layers · weighted scoring · conflict resolution · scenarios (no trade execution)

## Analysis Engine (Ch.6)

```
Spot · Futures · Options · Technical · Structure · Pattern · Volatility · Liquidity
        ↓
 Scoring → Conflict Resolution → Scenarios → MarketAnalysisOutput → (AI later)
```

API: `GET /api/v1/market/analysis` · CLI: `python -m src.main analyze`

## Design Book

| Chapter | Topic | Status |
|---------|--------|--------|
| 01–05 | Intro → Backend | ✅ |
| 06 | Analysis Engine | ✅ |
| 07–08 | … | Pending |

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

Rewrite in progress. Chapters 1–6 applied. Awaiting Chapters 7–8 (AI Decision / Outlook).
