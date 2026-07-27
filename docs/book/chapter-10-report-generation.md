# BTC Analyzer Enterprise Design Book
## Chapter 10 — Report Generation & Intelligence Delivery
**Version:** 1.0

> Canonical presentation-layer specification. Source: Enterprise Design Book, Chapter 10.

---

### 10.1 Purpose

Format validated intelligence for human and machine consumption.
**Does not analyze or score.** Presentation must never modify analytical values.

### 10.2 Pipeline

```
Analysis → AI Decision → Decision Object → Report Generator
→ API / Dashboard / Telegram / Export / Alerts → End User
```

### 10.3 Package Mapping

| Spec | Code |
|------|------|
| Contracts / schema | `src/reports/contracts.py` |
| Builder | `src/reports/builder.py` |
| Audience views | `src/reports/audiences.py` |
| QA gate | `src/reports/qa.py` |
| Alerts | `src/reports/alerts.py` |
| Localization | `src/reports/localization.py` |
| Channels | `src/reports/channels/` |
| Engine | `src/reports/engine.py` |
| Service | `src/services/reports.py` |
| Telegram delivery | `src/notifier/` |
