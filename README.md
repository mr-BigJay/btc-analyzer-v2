# BTC Analyzer v3

Professional crypto **market intelligence** and **decision support** platform.

> Evidence-based analysis. No single indicator, exchange, or model decides alone.

## Vision

Collect multi-source market data → validate narratives → analyze futures & options →
map technical structure → AI Decision Engine → **Daily Outlook** + **Intraday Trading Plan** →
Bitunix execution validation.

## Architecture

```
CoinEx Narrative
  └─► Binance Futures (Funding · OI · CVD · Order Flow · Liquidations)
        └─► Deribit Options (PCR · Max Pain · IV · Gamma · Dealer)
              └─► Technical Structure
                    └─► AI Decision Engine
                          ├─► Daily Outlook (03:30 UTC)
                          ├─► Intraday Trading Plan
                          └─► Bitunix Execution Validation
```

## Design Documents

Implementation follows the Software Design Document series:

| Doc | Topic | Status |
|-----|--------|--------|
| 01 | Project Vision & Architecture | ✅ In repo |
| 02 | … | Pending |
| 03 | … | Pending |
| 04 | … | Pending |
| 05 | … | Pending |
| 06 | … | Pending |
| 07 | … | Pending |
| 08 | … | Pending |

See [`docs/01-vision-architecture.md`](docs/01-vision-architecture.md).

## Package Layout

```
src/
├── collectors/
│   ├── coinex/          # Narrative analysis
│   ├── binance/         # Futures market reference
│   └── deribit/         # Options intelligence
├── technical/           # Structure, S/R, patterns, indicators
├── engine/              # AI Decision Engine (probabilities)
├── outlook/             # Daily Outlook generator
├── trading/             # Intraday Trading Plan
├── execution/
│   └── bitunix/         # Pre-trade execution validation
├── api/                 # FastAPI surface
├── notifier/            # Alerts (Telegram, etc.)
├── db/                  # Persistence
├── scheduler.py         # Jobs (Daily Outlook @ 03:30, intraday)
├── config.py
└── main.py              # CLI
frontend/                # Decision-support dashboard
docs/                    # Design documents
```

## Core Philosophy

1. **Multi-evidence only** — no isolated signal may open a trade
2. **Daily Outlook first** — strategic map before intraday setups
3. **Outlook ≠ signal** — outlook guides; trading plan proposes; Bitunix validates
4. **No certainty claims** — probabilities and invalidations, not guarantees

## Status

**Rewrite in progress.** Previous v2 codebase has been fully removed.
Awaiting Design Documents 02–08 for module-level specification and implementation.
