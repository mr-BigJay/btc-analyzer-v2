# BTC Analyzer Enterprise Design Book
## Chapter 14 — Backtesting, Performance Evaluation & Continuous Validation
**Version:** 1.0

> Objective measurement of analytical performance. Separates prediction quality from trading profitability. Historical evidence is immutable.

---

### 14.1 Purpose

Replay markets, archive predictions, evaluate outcomes, calibrate confidence, detect drift, and govern model releases with evidence.

### 14.2 Pipeline

```
Historical Data → Replay → Analysis → AI Decision → Prediction Archive
→ Market Outcome → Performance Evaluation → Validation Dashboard
```

### 14.3 Package Mapping

| Spec | Code |
|------|------|
| Contracts / Validation Object | `src/validation/contracts.py` |
| Prediction archive | `src/validation/archive.py` |
| Replay / walk-forward | `src/validation/replay.py`, `walk_forward.py` |
| Paper / shadow | `src/validation/paper.py`, `shadow.py` |
| Outcomes / metrics | `src/validation/outcomes.py`, `metrics.py` |
| Calibration / regimes / layers | `src/validation/calibration.py`, `regimes.py`, `layers.py` |
| Drift / failures | `src/validation/drift.py`, `failures.py` |
| Governance | `src/validation/governance.py` |
| Dashboard | `src/validation/dashboard.py` |
| Engine / service / API | `src/validation/engine.py`, `src/services/validation.py`, `/api/v1/validation/*` |

### 14.4 Validation Methods

Historical Backtesting · Walk-Forward · Paper Trading · Shadow Mode · Continuous Validation

### 14.5 Horizons

1h · 4h · 24h · 7d — evaluated independently.

### 14.6 Principles

Measure everything · No lookahead · Immutable archives · Evidence before promotion · Feedback without rewriting history.
