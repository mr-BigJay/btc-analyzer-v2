# BTC Analyzer v3

Professional AI-powered **crypto market intelligence** platform.
Designed as a **Decision Support System (DSS)** — evidence-based scenarios, not guaranteed direction.

> Enterprise Design Book is the source of truth for implementation.

## Core Principles (Ch.1 §1.5)

1. **Evidence-Based Analysis** — multiple independent sources
2. **Probability Over Prediction** — no absolute claims
3. **Modular Architecture** — replaceable components
4. **Transparency** — every recommendation includes reasoning
5. **Risk First** — risk over trade frequency

## High-Level Workflow (Ch.1 §1.7)

```
Data Collection
  → Data Validation
    → Data Normalization
      → Analysis Engine
        → Probability Engine
          → Daily Outlook (03:30)
            → Intraday Trading Plan
              → Trade Execution Validation (Bitunix)
```

## Scope v1.0 (Ch.1 §1.6)

Bitcoin · Binance Futures · Deribit Options · CoinEx Daily Analysis ·
Bitunix validation · Technical Analysis · AI Decision Engine ·
Daily Outlook · Intraday Trading Plan

## Design Book

| Chapter | Topic | Status |
|---------|--------|--------|
| 01 | Introduction | ✅ [`docs/book/chapter-01-introduction.md`](docs/book/chapter-01-introduction.md) |
| 02 | … | Pending |
| 03 | … | Pending |
| 04 | … | Pending |
| 05 | … | Pending |
| 06 | … | Pending |
| 07 | … | Pending |
| 08 | … | Pending |

## Package Layout

```
src/
├── collectors/          # CoinEx · Binance · Deribit
├── pipeline/            # Validation · Normalization
├── technical/           # Structure · S/R · patterns · indicators
├── engine/              # AnalysisEngine · ProbabilityEngine
├── outlook/             # Daily Outlook (03:30)
├── trading/             # Intraday Trading Plan
├── execution/bitunix/   # Execution validation
├── api/ · db/ · notifier/
├── scheduler.py
└── main.py
docs/book/               # Enterprise Design Book chapters
frontend/                # Decision-support UI
```

## Status

**Rewrite in progress.** Legacy v2 code removed.
Chapter 1 foundation applied. Awaiting Chapters 2–8.
