# BTC Analyzer Enterprise Design Book
## Chapter 9 — Scoring & Decision Model
**Version:** 1.0

> Canonical quantitative scoring specification. Source: Enterprise Design Book, Chapter 9.

---

### 9.1 Purpose

Convert every analytical layer into normalized numerical scores, dynamically weight them by regime, and produce objective decision metrics **before** AI reasoning.

### 9.2 Pipeline

```
Layer Outputs → Normalization → Layer Scores → Dynamic Weighting
→ Composite Scores → Decision Matrix → Market Bias → AI Decision Engine
```

### 9.3 Key Metrics

| Metric | Range | Meaning |
|--------|-------|---------|
| Layer score | -100 … +100 | Bearish ← Neutral → Bullish |
| Market Bias Score (MBS) | -100 … +100 | Directional bias |
| Confidence Score (CS) | 0 … 100 | Assessment confidence |
| Risk Score (RS) | 0 … 100 | Execution risk |
| MHI / MSI | 0 … 100 | Quality / stress (via Ch.8) |
| Data Quality Score (DQS) | 0 … 100 | Feed integrity |

### 9.4 Package Mapping

| Spec | Code |
|------|------|
| Contracts | `src/scoring/contracts.py` |
| Layer scores | `src/scoring/layers.py` |
| Dynamic weights | `src/scoring/weights.py` |
| Composites / matrix | `src/scoring/composites.py` |
| Confidence / conflict / MTF | `src/scoring/confidence.py` |
| Data quality | `src/scoring/quality.py` |
| Decision rules | `src/scoring/rules.py` |
| Validation records | `src/scoring/validation.py` |
| Engine | `src/scoring/engine.py` |
| Service | `src/services/scoring.py` |
