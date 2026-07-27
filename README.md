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
**Ch.8:** Market Intelligence · regime/cycle · MHI/MSI · participants · transitions

## Pipeline

```
Analysis Engine (8 layers)
        ↓
 Market Intelligence Framework (regime · cycle · MHI · MSI · liquidity · macro)
        ↓
 AI Decision Engine → Daily Outlook + Trading Plan
```

API:  
`/api/v1/market/analysis` · `/intelligence` · `/decision` · `/outlook` · `/trading-plan`  

CLI: `analyze` · `intelligence` · `outlook`

## Design Book

| Chapter | Topic | Status |
|---------|--------|--------|
| 01–08 | Intro → Market Intelligence | ✅ |

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
python -m src.main init-db
python -m src.main serve
python -m src.main intelligence
python -m src.main outlook
```

## Status

Chapters 1–8 applied on the rewrite branch.
