# BTC Analyzer Enterprise Design Book
## Chapter 4 — Database Design & Data Model
**Version:** 1.0

> Canonical database specification. Source: Enterprise Design Book, Chapter 4.

---

### 4.1 Philosophy

The database is the **Single Source of Truth (SSOT)**. All modules read/write only through the Central Repository.

Priorities: high write throughput · fast analytical queries · historical preservation · multi-asset/exchange scale · auditability.

### 4.2 Technology

| Component | Technology |
|-----------|------------|
| Primary DB | PostgreSQL (SQLite allowed for local/dev) |
| Cache | Redis (+ in-process memory fallback) |
| ORM | SQLAlchemy 2.x |
| Migration | Alembic |
| Time-series | PostgreSQL monthly partitioning (prod) |

### 4.3 Domains

1. **Market Data** — candles, trades, funding, OI, liquidations, order book  
2. **Technical Analysis** — EMA/RSI/MACD/VWAP/ATR, patterns, structure  
3. **Options Analytics** — IV, PCR, max pain, greeks, chain  
4. **AI Analysis** — CoinEx narrative, daily outlook, trading plans  
5. **System** — scheduler / API / error logs  
6. **Configuration** — exchanges, symbols, settings  

### 4.4 Core Tables

`symbols` · `exchanges` · `market_candles` · `funding_rates` · `open_interest` · `liquidations` · `orderbook_snapshot` · `trades` · `options_chain` · `technical_indicators` · `chart_patterns` · `market_structure` · `coinex_analysis` · `daily_outlook` · `trading_plan` · `scheduler_logs` · `api_call_logs` · `error_logs` · `system_settings`

### 4.5 Integrity & Naming

- PK `id`, FK `<table>_id`, UTC `timestamp`, snake_case  
- No orphan records (FK required for market rows)  
- Indexes: `symbol_id`, `exchange_id`, `timestamp`, `timeframe`, composites  

### 4.6 Retention

| Data | Retention |
|------|-----------|
| Trades | 90 days |
| Order book | 30 days |
| Candles / Funding / Options / Outlook / Plans | Permanent |

### Package Mapping

| Spec | Code |
|------|------|
| Models | `src/db/models/` |
| Engine/session | `src/db/session.py` |
| Seed | `src/db/seed.py` |
| Retention | `src/db/retention.py` |
| Alembic | `alembic/` |
| Repository | `src/storage/repository.py` |
| Redis | `src/storage/redis_cache.py` |
