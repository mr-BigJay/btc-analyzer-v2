# BTC Analyzer Enterprise Design Book
## Chapter 8 — Market Intelligence Framework
**Version:** 1.0

> Canonical strategic-context specification. Source: Enterprise Design Book, Chapter 8.

---

### 8.1 Purpose

Answer *context* questions before direction:
phase · who controls price · driving forces · trend sustainability · what changes next.

### 8.2 Pipeline Position

```
Market Data → Analysis Engine → Market Intelligence Framework → AI Decision Engine
```

### 8.3 Outputs (§8.15)

`MarketIntelligenceOutput` — regime, cycle, dominant participant, institutional activity,
MHI, MSI, volatility regime, macro/cross-asset bias, liquidity state, transition probability.

### 8.4 Package Mapping

| Spec | Code |
|------|------|
| Contracts | `src/intelligence/contracts.py` |
| Regime / Cycle | `src/intelligence/regime.py`, `cycle.py` |
| Participants / Institutions | `src/intelligence/participants.py` |
| Liquidity / Derivatives / Vol | `src/intelligence/{liquidity,derivatives,volatility}.py` |
| Macro / Cross-asset | `src/intelligence/{macro,cross_asset}.py` |
| MHI / MSI / Transitions | `src/intelligence/{health,stress,transitions}.py` |
| Engine | `src/intelligence/engine.py` |
| Service | `src/services/intelligence.py` |

### 8.5 Principles

Context before direction · participants before price · separate quality (MHI) from stress (MSI)
· early transitions · deterministic · never fabricate missing macro/cross-asset data.
