# BTC Analyzer v3

Professional AI-powered **crypto market intelligence** platform.
**Decision Support System (DSS)** — evidence-based scenarios, not guaranteed direction.

> Enterprise Design Book is the source of truth.

## Core Principles

**Ch.1:** Evidence-Based · Probability Over Prediction · Modular · Transparency · Risk-First  
**Ch.2:** Separation of Concerns · Loose Coupling · High Cohesion · Event Driven · AI Assisted  
**Ch.3:** Collect ≠ Analyze · Validate everything · Append-only history · Never halt on API failure  
**Ch.4:** Database is SSOT · PostgreSQL + Redis · FK integrity · Retention · Alembic migrations

## Database (Ch.4)

```
Collectors → Normalized Data → PostgreSQL
                                ├─ Historical tables
                                └─ Redis / cached views
                                     ↓
                              Analysis → Decision → Dashboard
```

**Domains:** Market Data · Technical · Options · AI · System · Configuration  

**Stack:** PostgreSQL (SQLite local) · Redis · SQLAlchemy · Alembic  

**Retention:** trades 90d · order book 30d · candles/funding/options/outlook permanent

## Data Collection Engine (Ch.3)

| Provider | Role | Priority |
|----------|------|----------|
| Binance | Futures market reference | Critical |
| Deribit | Options intelligence | Critical |
| CoinEx | Daily narrative (**AI Research** tab) | High |
| Bitunix | Execution validation only | Medium |

## Design Book

| Chapter | Topic | Status |
|---------|--------|--------|
| 01 | Introduction | ✅ |
| 02 | System Architecture | ✅ |
| 03 | Data Collection Engine | ✅ |
| 04 | Database Design & Data Model | ✅ |
| 05–08 | … | Pending |

See [`docs/book/`](docs/book/).

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.main init-db
# optional: python -m src.main migrate
python -m src.main collect
python -m src.main serve
```

### Docker (Postgres + Redis)

```bash
docker compose up -d
```

## Status

Rewrite in progress. Chapters 1–4 applied. Awaiting Chapters 5–8.
