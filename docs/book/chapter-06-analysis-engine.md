# BTC Analyzer Enterprise Design Book
## Chapter 6 — Analysis Engine (Core Intelligence)
**Version:** 1.0

> Canonical analysis-engine specification. Source: Enterprise Design Book, Chapter 6.

---

### 6.1 Purpose

Transform validated market data into structured, weighted intelligence.
**Does not execute trades.** Output feeds the AI Decision Engine.

### 6.2 Eight Layers

| Layer | Question |
|-------|----------|
| Spot | Who is buying/selling? |
| Futures | How leveraged is the market? |
| Options | What are professionals pricing? |
| Technical | What is price structure? |
| Market Structure | Is trend healthy? |
| Pattern | What formations exist? |
| Volatility | Expansion or compression? |
| Liquidity | Where are stop clusters? |

### 6.3 Pipeline

```
Raw → Validate → Normalize → Layer Analysis → Scoring → Conflict Resolution
→ Market Bias → (AI Reasoning) → Daily Outlook
```

### 6.4 Standard Layer Object

```json
{
  "layer": "Futures",
  "signal": "Bullish",
  "confidence": 81,
  "strength": "High",
  "summary": "…"
}
```

Confidence 0–100. Weights are dynamic (default Spot/Futures/Options 20% each).

### 6.5 Package Mapping

| Spec | Code |
|------|------|
| Contracts | `src/analysis/contracts.py` |
| Context | `src/analysis/context.py` |
| Layers | `src/analysis/layers/` |
| Scoring / Weights / Conflict | `src/analysis/{scoring,weights,conflict}.py` |
| Scenarios | `src/analysis/scenarios.py` |
| Engine | `src/analysis/engine.py` |
| Service | `src/services/analysis.py` |
