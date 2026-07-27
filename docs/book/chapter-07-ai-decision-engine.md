# BTC Analyzer Enterprise Design Book
## Chapter 7 — AI Decision Engine
**Version:** 1.0

> Canonical cognitive-layer specification. Source: Enterprise Design Book, Chapter 7.

---

### 7.1 Purpose

Consume structured Analysis Engine outputs and produce explainable, probabilistic market intelligence.
**Never accesses raw exchange data.** Never executes trades.

### 7.2 Pipeline

```
Analysis Output → Evidence Aggregation → Signal Prioritization → Conflict Explanation
→ Narrative Detection → Scenario Reasoning → Probability Estimation → Risk Assessment
→ NLG → Daily Outlook / Intraday Trading Plan
```

### 7.3 Constraints (§7.15)

- No price guarantees or certainty claims
- Never ignore conflicting evidence
- Never fabricate missing data
- Identical inputs → identical outputs (deterministic core)
- Elevated uncertainty when evidence is insufficient

### 7.4 Package Mapping

| Spec | Code |
|------|------|
| Contracts / schema | `src/ai/contracts.py` |
| Evidence + priority | `src/ai/evidence.py` |
| Narrative detection | `src/ai/narrative.py` |
| Probability + scenarios | `src/ai/probability.py` |
| Risk assessment | `src/ai/risk.py` |
| Explainability / NLG | `src/ai/explain.py`, `src/ai/nlg.py` |
| Daily Outlook | `src/ai/outlook.py` |
| Trading Plan | `src/ai/trading_plan.py` |
| Learning records | `src/ai/learning.py` |
| Engine | `src/ai/engine.py` |
| Service | `src/services/decision.py` |

### 7.5 Output Schema (§7.16)

`AIDecisionReport` — market_bias, confidence, regime, risk, primary_narrative,
scenarios, key_drivers, major_risks, trading_plan, reasoning, daily_outlook.
