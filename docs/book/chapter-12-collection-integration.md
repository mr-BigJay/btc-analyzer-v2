# BTC Analyzer Enterprise Design Book
## Chapter 12 — Data Collection & Exchange Integration Layer
**Version:** 1.0

> Single gateway between BTC Analyzer and external market data. Builds on Chapter 3; no downstream component calls exchange APIs directly.

---

### 12.1 Purpose

Acquire, validate, normalize, and distribute market data from external providers with high availability, fault tolerance, and exchange independence.

### 12.2 Pipeline

```
External Providers (REST / WebSocket / Files)
→ Collector Framework → Validation → Normalization
→ Internal Event Bus → PostgreSQL / Redis / Analysis
```

### 12.3 Package Mapping

| Spec | Code |
|------|------|
| ExchangeCollector interface | `src/collectors/interface.py` |
| Internal data contract | `src/collectors/contract.py` |
| Event bus | `src/collectors/events.py` |
| Symbol registry | `src/collectors/symbols.py` |
| Health monitor | `src/collectors/health.py` |
| Quarantine | `src/collectors/quarantine.py` |
| Metrics / DQS inputs | `src/collectors/metrics.py` |
| Typed collectors | `src/collectors/typed.py` |
| Historical backfill | `src/collectors/backfill.py` |
| Orchestration | `src/collectors/engine.py` |
| Exchange adapters | `src/collectors/{binance,deribit,coinex,bitunix}/` |
| Validation / normalize | `src/pipeline/` |

### 12.4 Supported Exchanges

| Exchange | Scope |
|----------|-------|
| Binance | Spot, Futures |
| Deribit | Options |
| CoinEx | Market metrics / narrative |
| Bitunix | Futures metrics (validation only) |

Future adapters only: Bybit, OKX, CME, Hyperliquid, Kraken, Coinbase.

### 12.5 Collector Interface

```
connect() → collect() → validate() → normalize() → publish()
```

Every collector is independently restartable.

### 12.6 Collector Types

Spot · Futures · Options · Volatility · Macro

### 12.7 Acquisition Modes

Streaming (WS) · Polling (REST) · Scheduled import

### 12.8 Timestamps

Every record stores exchange / collection / processing timestamps (ISO-8601 UTC).

### 12.9 Quarantine

Invalid records never reach analysis; stored in quarantine for audit.

### 12.10 Events

Normalized data published as `market.<domain>.updated` events.

### 12.11 Health States

`Healthy` · `Degraded` · `Recovering` · `Offline`

### 12.12 Performance Targets

| Metric | Target |
|--------|--------|
| Spot latency | < 250 ms |
| WS reconnect | < 5 s |
| Validation | < 10 ms |
| Normalization | < 5 ms |
| API availability | ≥ 99.9% |
| Collector uptime | ≥ 99.95% |
