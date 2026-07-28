# BTC Analyzer Enterprise Design Book
## Chapter 16 — Alerting, Notification & Event Processing Engine
**Version:** 1.0

> Event-driven monitoring of analytical outputs. Deterministic detection, correlation, deduplication, and multi-channel delivery with immutable archives. Operates independently from report generation.

---

### 16.1 Purpose

Deliver timely, relevant, actionable notifications while minimizing noise and duplicates.

### 16.2 Pipeline

```
Detection → Validation → Classification → Correlation → Deduplication
→ Priority → Notification → Archive
```

### 16.3 Package Mapping

| Spec | Code |
|------|------|
| Event Object / severity / state | `src/events/contracts.py` |
| Detection rules | `src/events/detection.py` |
| Correlation | `src/events/correlation.py` |
| Deduplication | `src/events/dedupe.py` |
| Routing / rate limits | `src/events/routing.py`, `rate_limit.py` |
| Delivery / formatters | `src/events/delivery.py`, `formatters.py` |
| Archive / analytics | `src/events/archive.py`, `analytics.py` |
| Engine / service / API | `src/events/engine.py`, `src/services/events.py`, `/api/v1/events/*` |

### 16.4 Categories

Price · Trend · Futures · Options · Liquidity · Risk · System · Macro

### 16.5 Severity

Informational · Low · Medium · High · Critical

### 16.6 Channels

API · Dashboard · Telegram · WebSocket (severity-gated; Critical hits all)

### 16.7 Governance

No event bypasses validation · Deterministic rules · Immutable archive · Critical bypasses rate limits · Idempotent replay
