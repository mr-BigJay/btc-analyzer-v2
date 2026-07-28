# BTC Analyzer Enterprise Design Book
## Chapter 13 — Market Data Standardization & Feature Engineering
**Version:** 1.0

> Transforms normalized market observations into deterministic, versioned analytical features for the Analysis Engine.

---

### 13.1 Purpose

Observations → measurable intelligence. Every feature must be deterministic, explainable, time-aware, normalized, and versioned.

### 13.2 Pipeline

```
Normalized Data → Cleaning → Feature Engineering → Derived Indicators
→ Composite Features → Validation → Feature Store → Analysis Engine
```

### 13.3 Package Mapping

| Spec | Code |
|------|------|
| Contracts / versioning | `src/features/contracts.py` |
| Cleaning / outliers | `src/features/cleaning.py`, `outliers.py` |
| Category calculators | `src/features/categories/` |
| Composites | `src/features/composite.py` |
| Normalization | `src/features/normalize.py` |
| Validation / quarantine | `src/features/validation.py` |
| Feature store | `src/features/store.py` + DB `feature_store` |
| MTF sync | `src/features/mtf.py` |
| Engine | `src/features/engine.py` |
| Service / API | `src/services/features.py`, `/api/v1/features/*` |

### 13.4 Categories

Price · Volume · Derivatives · Options · Technical · Structural · Liquidity · Volatility · Composite

### 13.5 Normalization Ranges

Directional −100…+100 · Probability 0…100 · Ratio 0…1

### 13.6 Missing Data

Never fabricate. Forward-fill where valid, null propagation, confidence/DQS reduction.

### 13.7 Feature Store Record

name, asset, timeframe, timestamp, value, feature_version, source lineage

### 13.8 Performance Targets

Generation &lt; 20 ms · Normalize &lt; 5 ms · Validate &lt; 10 ms · Store &lt; 15 ms · Total &lt; 50 ms
