# BTC Analyzer Enterprise Design Book
## Chapter 11 — Data Model & Database Architecture
**Version:** 1.0

> Canonical long-term memory specification. Builds on Chapter 4; adds Ch.11 analytical/decision/reporting entities.

---

### 11.1 Layered Storage

```
External Sources → Collection → Raw Market Storage → Normalized Analytical DB
→ Analysis DB · AI Memory DB · Reporting DB
```

Primary: **PostgreSQL** · Cache: **Redis** · Object/Backup storage for archives · Dev: SQLite allowed.

### 11.2 Data Classes

| Class | Examples |
|-------|----------|
| Market | price, volume, funding, OI, options |
| Analytical | indicators, structure, liquidity, volatility |
| Decision | scores, AI decisions, scenarios |
| Operational | logs, reports, alerts |

### 11.3 Package Mapping

| Spec | Code |
|------|------|
| Core Ch.4 tables | `src/db/models/{market,options,technical,ai,config,system}.py` |
| Ch.11 extensions | `src/db/models/intelligence_store.py` |
| Access rules | `src/db/access.py` |
| Intelligence writers | `src/db/repositories/intelligence_repo.py` |
| Data packages | `src/db/packages.py` |
| Retention | `src/db/retention.py` |
| Central facade | `src/storage/repository.py` |
| Migration | `alembic/versions/0002_ch11_schema.py` |
| API package | `GET /api/v1/db/package` |

### 11.4 Aliases

Ch.11 `assets` ↔ `symbols` · Ch.11 `options_data` ↔ `options_analytics` (+ `options_data` snapshot table).

### 11.5 Core Entities

`assets`/`symbols`, `exchanges`, `spot_data`, `futures_data`, `options_data`, `volatility_data`,
`technical_indicators`, `market_structure`, `liquidity_zones`, `market_scores`, `ai_decisions`,
`reports`, `alerts`, plus Ch.4 market/system tables.

### 11.6 Access Rules (§11.25)

| Module | WRITE |
|--------|-------|
| collector | market + spot/futures/options snapshots |
| analysis | technical, structure, liquidity, volatility |
| scoring | market_scores |
| ai | ai_decisions, outlook, plan |
| reporting | reports, alerts |

### 11.7 Data Package (§11.26)

```json
{
  "asset": "BTCUSDT",
  "timestamp": "...",
  "market_data": {},
  "analysis": {},
  "scores": {},
  "decision": {}
}
```

### 11.8 Retention (§11.21)

| Data | Retention |
|------|-----------|
| Tick candles | 14 days |
| Trades | 90 days |
| Order book | 30 days |
| Logs | 30–90 days |
| Analysis / scores / AI / reports | Permanent |

### 11.9 Versioning (§11.22)

Analytical outputs store `engine_version`, `calculation_version` / `ai_version`, and timestamps for reconstruction.

### 11.10 Partitioning (§11.19)

PostgreSQL production may partition `futures_data` / `spot_data` by month (`futures_data_YYYY_MM`). SQLite local/dev uses flat tables.
