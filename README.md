# BTC Analyzer v3

Professional AI-powered **crypto market intelligence** platform.
**Decision Support System (DSS)** — evidence-based scenarios, not guaranteed direction.

## Pipeline

```
Collect → Features → Analysis → Intelligence → Scoring → Risk Engine → AI Decision → Reports
                                                              ↓                    ↓
                                                         Validation           Event Engine
                                                                              (alerts / WS / Telegram)
```

## CLI

```bash
python -m src.main analyze
python -m src.main intelligence
python -m src.main score
python -m src.main outlook    # Ch.10 formatted Daily Outlook
python -m src.main report     # executive markdown
```

## Design Book

| Chapter | Topic | Status |
|---------|--------|--------|
| 01–10 | Intro → Report Generation | ✅ |
| 11 | Data Model & Database Architecture | ✅ |
| 12 | Data Collection & Exchange Integration | ✅ |
| 13 | Feature Engineering | ✅ |
| 14 | Backtesting & Continuous Validation | ✅ |
| 15 | Risk Management & Capital Preservation | ✅ |
| 16 | Alerting, Notification & Event Processing | ✅ |
| 17 | Dashboard, Visualization & User Experience | ✅ |
| 18 | API Specification & Integration Guide | ✅ |
| 19 | Security, Authentication & Operational Hardening | ✅ |
| 20 | Deployment, DevOps & Infrastructure | ✅ |
| 21 | Monitoring, Logging & Observability | ✅ |
| 22 | Testing Strategy & Quality Assurance | ✅ |

## Status

Chapters 1–22 applied on the rewrite branch.
