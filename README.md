# BTC Analyzer v3

Professional AI-powered **crypto market intelligence** platform.
**Decision Support System (DSS)** — evidence-based scenarios, not guaranteed direction.

> Enterprise Design Book is the source of truth.

## Core Principles

**Ch.1:** Evidence-Based · Probability Over Prediction · Modular · Transparency · Risk-First  
**Ch.2:** Separation of Concerns · Loose Coupling · High Cohesion · Event Driven · AI Assisted

## 8-Layer Architecture (Ch.2)

```
1 Data Sources      → Binance · Deribit · CoinEx · Bitunix
2 Collection        → Raw market data (retry, rate limits)
3 Validation        → Dedup, timestamps, integrity
4 Normalization     → Internal format (BTCUSDT)
5 Storage           → Central Repository · cache · snapshots
6 Analysis          → Futures · Options · Technical · Pattern · Structure
7 AI                → Decision Engine · Probability Engine
8 Presentation      → Daily Outlook · Intraday Plan · Dashboard · Alerts
```

## Object Flow (Ch.2 §2.6)

```
CoinEx → Narrative Object
Binance → Flow Object          (futures market reference)
Deribit → Options Object
Technical → Chart Object
        ↓
 Decision Engine → Probability Object
        ↓
 Daily Outlook → Intraday Setup → Bitunix Validation
```

## Design Rules (mandatory)

1. No cross-module DB access — use Central Repository  
2. Standardized `ModuleResult` envelopes only  
3. UTC timestamps  
4. Confidence on every analysis  
5. Explainable recommendations  
6. **Only Decision Engine** generates trading recommendations  
7. Bitunix = execution validation only  
8. Binance = futures market reference  
9. AI-ready modules without redesign  
10. Exchange-independent collectors  

## Design Book

| Chapter | Topic | Status |
|---------|--------|--------|
| 01 | Introduction | ✅ |
| 02 | System Architecture | ✅ |
| 03–08 | … | Pending |

See [`docs/book/`](docs/book/).

## Package Layout

```
src/
├── core/                # ModuleResult + domain objects
├── collectors/          # Layer 2: CoinEx · Binance · Deribit
├── pipeline/            # Layers 3–4: Validation · Normalization
├── storage/             # Layer 5: Central Repository
├── analysis/            # Layer 6: Futures · Options · Technical · Pattern · Structure
├── engine/              # Layer 7: Decision · Probability
├── outlook/ · trading/  # Layer 8 presentation outputs
├── execution/bitunix/   # Execution validation only
├── api/ · db/ · notifier/
└── main.py
```

## Status

Rewrite in progress. Chapters 1–2 applied. Awaiting Chapters 3–8.
