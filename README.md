# BTC Analyzer v3

Professional AI-powered **crypto market intelligence** platform.
**Decision Support System (DSS)** — evidence-based scenarios, not guaranteed direction.

> Enterprise Design Book is the source of truth.

## Pipeline

```
Analysis Engine (8 layers)
        ↓
 Market Intelligence (regime · cycle · MHI · MSI)
        ↓
 Scoring & Decision Model (MBS · CS · RS · DQS · publish gate)
        ↓
 AI Decision Engine → Daily Outlook + Trading Plan
```

## CLI

```bash
python -m src.main analyze
python -m src.main intelligence
python -m src.main score
python -m src.main outlook
```

## Design Book

| Chapter | Topic | Status |
|---------|--------|--------|
| 01–09 | Intro → Scoring & Decision Model | ✅ |

## Status

Chapters 1–9 applied on the rewrite branch.
