# BTC Analyzer Enterprise Design Book
## Chapter 15 — Risk Management & Capital Preservation Framework
**Version:** 1.0

> Execution risk is evaluated independently from market direction. Capital preservation has priority over opportunity frequency. AI cannot override mandatory risk controls.

---

### 15.1 Purpose

Filter every trading recommendation through quantitative risk controls before publication. A strong directional signal does not justify a position by itself.

### 15.2 Pipeline

```
Market Intelligence → Scoring → Risk Engine
→ Exposure Sizing · Position Limits · Trade Filter → Final Trading Plan
```

### 15.3 Package Mapping

| Spec | Code |
|------|------|
| Risk Object / levels | `src/risk/contracts.py` |
| Category scores | `src/risk/categories.py` |
| Composite Risk Score | `src/risk/crs.py` |
| Position sizing | `src/risk/sizing.py` |
| No Trade Zone | `src/risk/no_trade.py` |
| Confidence×Risk matrix | `src/risk/matrix.py` |
| Explanations | `src/risk/explain.py` |
| Engine / service / API | `src/risk/engine.py`, `src/services/risk.py`, `/api/v1/risk/*` |

### 15.4 CRS Bands

0–20 Very Low · 21–40 Low · 41–60 Moderate · 61–80 High · 81–100 Extreme

### 15.5 Risk Categories

Market · Liquidity · Volatility · Leverage · Event · Data · Execution (each scored 0–100 before weighted CRS aggregation).

### 15.6 No Trade Zone

Triggered by low DQS, extreme MSI, conflicting layers, macro windows, exchange degradation, unresolved validation, CRS ≥ 81, closed publish gate, High Uncertainty, or critical liquidity. Reasons are always logged.

### 15.7 Governance

Deterministic · Reproducible · AI cannot bypass · Suppressed recommendations logged with reason · Risk Object attached to AI decision package and reports
