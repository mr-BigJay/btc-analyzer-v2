# BTC Analyzer v3

Professional AI-powered **crypto market intelligence** platform.
**Decision Support System (DSS)** — evidence-based scenarios, not guaranteed direction.

> Enterprise Design Book is the source of truth.

## Core Principles

**Ch.1:** Evidence-Based · Probability Over Prediction · Modular · Transparency · Risk-First  
**Ch.2:** Separation of Concerns · Loose Coupling · High Cohesion · Event Driven · AI Assisted  
**Ch.3:** Collect ≠ Analyze · Validate everything · Append-only history · Never halt on API failure

## Data Collection Engine (Ch.3)

```
External APIs → Collectors → Validators → Normalizers → Cache → Database → Analysis
```

| Provider | Role | Priority |
|----------|------|----------|
| Binance | Futures market reference | Critical |
| Deribit | Options intelligence | Critical |
| CoinEx | Daily narrative (**AI Research** tab on futures page) | High |
| Bitunix | Execution validation only | Medium |

**Scheduler:** realtime WS · 1m price/funding/OI · 5m technical cache · 1h options · daily outlook 03:30 UTC  
**Retry:** 5s → 15s → 30s → cached snapshot → continue  
**Secrets:** environment variables only (never in source)

## 8-Layer Architecture (Ch.2)

```
1 Data Sources → 2 Collection → 3 Validation → 4 Normalization
→ 5 Storage → 6 Analysis → 7 AI → 8 Presentation
```

## Design Book

| Chapter | Topic | Status |
|---------|--------|--------|
| 01 | Introduction | ✅ |
| 02 | System Architecture | ✅ |
| 03 | Data Collection Engine | ✅ |
| 04–08 | … | Pending |

See [`docs/book/`](docs/book/).

## Package Layout

```
src/
├── collectors/
│   ├── binance/ deribit/ coinex/ bitunix/   # isolated collectors
│   ├── engine.py                            # Collect→Validate→Normalize→Store
│   ├── http.py · websocket.py · common.py
├── pipeline/          # validation · normalization · quality
├── storage/           # Central Repository · memory cache
├── analysis/ · engine/ · outlook/ · trading/
└── main.py
```

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.main init-db
python -m src.main collect    # one collection cycle
python -m src.main run        # scheduler
python -m src.main serve      # API + dashboard
```

## Status

Rewrite in progress. Chapters 1–3 applied. Awaiting Chapters 4–8.
