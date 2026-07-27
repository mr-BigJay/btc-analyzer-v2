# BTC Analyzer — Software Design Document
## Document 1: Project Vision & Architecture

> Source of truth for Cursor implementation. Previous codebase has been fully removed.

---

### 1. Project Goal

Build a **professional crypto market intelligence and decision support system**.

The platform must not merely display indicators. It must:

1. Collect data from multiple independent sources
2. Validate market narratives
3. Analyze futures, options, and technical structure
4. Produce a **Daily Outlook** and an actionable **Trading Plan**

---

### 2. Core Philosophy

> Every trading conclusion must be supported by **multiple independent evidence layers**.

- No single indicator may generate a trading decision alone
- No single exchange or model may generate a trading decision alone
- Pattern detection alone must never trigger a trade

---

### 3. High-Level Architecture

```
CoinEx (Narrative)
    → Binance Futures (Market Reference)
        → Deribit Options (Options Intelligence)
            → Technical Analysis (Structure)
                → AI Decision Engine (Probabilities)
                    → Daily Outlook + Intraday Trading Plan
                        → Bitunix Execution Layer (Validation)
```

---

### 4. Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| **CoinEx** | Narrative analysis — what story is the market telling? |
| **Binance Futures** | Market reference: Funding, Open Interest, CVD, Order Flow, Liquidations |
| **Deribit Options** | Options intelligence: PCR, Max Pain, IV, Gamma, Dealer Position |
| **Technical Layer** | Market structure, support/resistance, patterns, indicators |
| **AI Decision Engine** | Combine all evidence layers and calculate probabilities |
| **Bitunix** | Execution validation before opening positions |

---

### 5. Main Outputs

#### Daily Outlook (scheduled ~03:30 UTC)
- Market bias (bullish / bearish / neutral)
- Expected daily candle color
- Expected range (high / low)
- Expected close zone
- Key support / resistance
- Scenarios (base / bull / bear)
- Invalidation levels
- Risk factors

> The Daily Outlook is a **strategic map**, not a direct trade signal.

#### Intraday Trading Plan
- Direction: Long / Short / No Trade
- Entry zone
- Stop loss
- Take profits
- Confidence score
- Risk / Reward

> Intraday setups are generated **only after** the Daily Outlook exists.

---

### 6. Decision Logic

A trade-ready conclusion requires confirmation across:

1. CoinEx narrative
2. Binance futures evidence
3. Deribit options evidence
4. Technical analysis structure
5. Risk management rules

---

### 7. Daily Outlook Concept

Strategic map for the day. Estimates:

- Bullish / bearish probabilities
- Expected candle color
- Expected daily high / low / close range
- Preferred trading direction
- Key levels and risk factors

---

### 8. Intraday Concept

Refines entry timing using:

- Lower timeframes
- Order flow
- Confirmation signals

Only after Daily Outlook is published.

---

### 9. Final Objective

Create a professional decision-support platform comparable in philosophy to institutional market intelligence systems. Help traders make **better evidence-based decisions** — never promise certainty.
