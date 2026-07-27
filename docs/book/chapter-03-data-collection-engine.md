# BTC Analyzer Enterprise Design Book
## Chapter 3 — Data Collection Engine
**Version:** 1.0

> Canonical data-acquisition specification. Source: Enterprise Design Book, Chapter 3.

---

### 3.1 Purpose

The Data Collection Engine acquires, validates, normalizes, and stores all external market data required by the BTC Analyzer platform.

**This layer must never perform market analysis.** Its sole responsibility is accurate, complete, standardized data for downstream components.

---

### 3.2 Objectives

- Collect from multiple exchanges simultaneously
- Support REST and WebSocket
- Validate every incoming dataset
- Normalize exchange formats into a unified internal model
- Cache frequently accessed data
- Store historical snapshots (append-only)
- Handle API failures gracefully
- Minimize latency while respecting rate limits

---

### 3.3 Data Sources (v1.0)

| Provider | Purpose | Priority |
|----------|---------|----------|
| Binance | Futures Market Reference | Critical |
| Deribit | Options Market Intelligence | Critical |
| CoinEx | Daily Narrative Analysis | High |
| Bitunix | Execution Validation | Medium |

Future: OKX, Bybit, Hyperliquid, CME, Glassnode, CryptoQuant, Santiment.

---

### 3.4 Pipeline

```
External APIs → Collectors → Validators → Normalizers → Cache → Database → Analysis Engine
```

---

### 3.5 Collector Design

Each exchange has an independent collector under `src/collectors/<exchange>/` containing:

- Authentication
- REST Client
- WebSocket Client
- Retry Handler
- Parser
- Logger

**No collector may communicate directly with another collector.**

---

### 3.6–3.9 Provider Scope

- **Binance:** Spot + Futures (funding, OI, L/S, premium, mark/index, basis) + WS streams
- **Deribit:** Option chain, Greeks, derived metrics (PCR, max pain, IV rank/percentile, GEX, skew)
- **CoinEx:** Daily narrative — publication time, summary, bull/bear args, S/R, confidence; raw + parsed stored separately
- **Bitunix:** Price, funding, order book, spread, OI, volume — never primary analytical source

---

### 3.10 Validation

Checks: API status, missing fields, invalid values, duplicates, timestamps, symbol, numerical precision.  
Invalid records must never enter the database.

### 3.11 Normalization

Unified symbols (e.g. `BTCUSDT`) and standard fields: `timestamp` (UTC), `symbol`, `exchange`, `price`, `volume`, `source_id`.

### 3.12 Cache

In-memory hot data: latest funding, OI, option chain, order book, active daily outlook.

### 3.13 Database

Append-only snapshots. Core tables: `futures_market`, `options_market`, `spot_market`, `coinex_analysis`, `technical_cache`, `orderbook_snapshot`, `liquidation_events`, `daily_outlook`, `intraday_signals`.

### 3.14 Scheduler

| Interval | Task |
|----------|------|
| Real-Time | Trades, Order Book, Liquidations |
| 1 Minute | Price, Funding, Open Interest |
| 5 Minutes | Technical Cache Refresh |
| 1 Hour | Option Chain Update |
| Daily 03:30 UTC | Daily Outlook Generation |

### 3.15 Retry Policy

Retry #1 (5s) → #2 (15s) → #3 (30s) → Fallback to Cached Snapshot → Log Warning → Continue.

### 3.16 Rate Limits

Request queue, exponential backoff, token bucket, automatic pause, priority scheduling.

### 3.17 Logging

Structured: timestamp, exchange, endpoint, response time, status, error code, retry count.

### 3.18 Security

API keys via environment variables only; HTTPS; read-only permissions preferred.

### 3.19 Data Quality

Complete · Accurate · Timely · Consistent · Normalized · Traceable.  
Failures → degraded dataset + reduced confidence.

---

### Package Mapping

| Spec | Code |
|------|------|
| Collectors | `src/collectors/{binance,deribit,coinex,bitunix}/` |
| Shared infra | `src/collectors/{http,websocket,base,common}.py` |
| Engine | `src/collectors/engine.py` |
| Validators | `src/pipeline/validation.py` |
| Normalizers | `src/pipeline/normalization.py` |
| Quality | `src/pipeline/quality.py` |
| Cache | `src/storage/cache.py` |
| Repository | `src/storage/repository.py` |
| Tables | `src/db/models.py` |
| Scheduler | `src/scheduler.py` |
