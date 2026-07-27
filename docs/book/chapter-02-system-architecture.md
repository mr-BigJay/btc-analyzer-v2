# BTC Analyzer Enterprise Design Book
## Chapter 2 — System Architecture
**Version:** 1.0

> Canonical architecture specification. Source: Enterprise Design Book, Chapter 2.

---

### 2.1 Overview

The BTC Analyzer platform is a **modular, service-oriented market intelligence system**. Each module has a single responsibility and communicates through standardized interfaces.

Goals of this architecture:

- Scalability
- Maintainability
- Future extensibility
- Independent development and testing of each subsystem

The platform follows a **layered architecture** where raw market data is transformed into actionable trading intelligence through sequential processing stages.

---

### 2.2 Design Philosophy

| Principle | Meaning |
|-----------|---------|
| **Separation of Concerns** | Each module performs only one task (Collection, Technical, Options, Decision are independent) |
| **Loose Coupling** | Modules communicate through standardized objects — never another module's implementation |
| **High Cohesion** | Domain functions stay inside their module (e.g. Funding never lives in Technical) |
| **Event Driven** | New data → Validation → Normalization → Analysis → AI Decision → Storage → Dashboard |
| **AI Assisted** | AI never replaces raw data — it interprets validated evidence |

Event chain:

```
Market Data → Validation → Normalization → Analysis → AI Decision → Storage → Dashboard Update
```

---

### 2.3 High-Level Architecture

```
                 CoinEx
        Daily Narrative Analysis
                    │
                    ▼
           Data Collection Layer
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
 Binance         Deribit         Bitunix
 Futures         Options       Execution
    │               │
    └───────┬───────┘
            ▼
    Data Validation Layer
            ▼
   Data Normalization Layer
            ▼
    Central Data Repository
            ▼
      Analysis Engine
            │
  ┌─────────┼─────────┐
  ▼         ▼         ▼
Futures  Options  Technical
Analysis Analysis Analysis
  └─────────┬─────────┘
            ▼
     AI Decision Engine
            ▼
     Probability Engine
            ▼
       Daily Outlook
            ▼
   Intraday Signal Engine
            ▼
    Execution Validation
            ▼
        Bitunix API
```

---

### 2.4 Layer Architecture (8 Layers)

| Layer | Name | Responsibility |
|-------|------|----------------|
| 1 | **Data Sources** | External providers (Binance, Deribit, CoinEx, Bitunix). No analysis. |
| 2 | **Collection** | API requests, WebSockets, retry, rate limits → Raw Market Data |
| 3 | **Validation** | Dedup, timestamps, missing values, API response checks → Validated Data |
| 4 | **Normalization** | One internal format (e.g. all symbols → `BTCUSDT`) |
| 5 | **Storage** | Historical storage, caching, snapshots, time-series |
| 6 | **Analysis** | Futures · Options · Technical · Pattern · Market Structure engines |
| 7 | **AI** | Combine results, probabilities, scenarios, reasoning |
| 8 | **Presentation** | Daily Outlook · Intraday Plan · Dashboard · Alerts · Reports |

---

### 2.5 Core Modules

#### CoinEx Module
- **Purpose:** Daily market narrative
- Download analysis · Extract scenarios · Parse support/resistance
- **Output:** Narrative Object

#### Binance Module
- **Purpose:** Market Reference (primary futures reference — Rule 8)
- Funding · OI · Liquidations · Trades · Depth · Order Book · Long/Short · Premium · Mark Price
- **Output:** Market Flow Object

#### Deribit Module
- **Purpose:** Institutional positioning
- Option Chain · PCR · IV · Greeks · Gamma · Dealer Position
- **Output:** Options Object

#### Technical Module
- **Purpose:** Chart intelligence
- EMA · VWAP · ATR · MACD · RSI · ADX · Bollinger · Fibonacci · Trend · S/R · Patterns
- **Output:** Technical (Chart) Object

#### Decision Engine
- Merge everything
- **Never trust one module alone**

---

### 2.6 Object Flow

```
CoinEx     → Narrative Object
Binance    → Flow Object
Deribit    → Options Object
Technical  → Chart Object
                ↓
         Decision Engine
                ↓
         Probability Object
                ↓
          Daily Outlook
                ↓
         Intraday Setup
```

---

### 2.7 Communication

Every module returns a standardized object:

```json
{
  "module": "Binance",
  "status": "OK",
  "timestamp": "...",
  "confidence": 0.91,
  "data": {}
}
```

No module directly modifies another module's output.

---

### 2.8 Scalability

New exchanges (OKX, Bybit, Hyperliquid, CME, Coinbase) require **only a new Collector**. All other layers remain unchanged.

---

### 2.9 Fault Tolerance

If one provider fails (e.g. Deribit offline):

1. Use latest cached snapshot
2. Continue other analyses (e.g. Futures)
3. Decrease confidence
4. Log warning
5. Continue system

**The platform must never stop because of one unavailable provider.**

---

### 2.10 Design Rules (Mandatory)

1. No module may directly call another module's database tables
2. All communication through standardized interfaces
3. All timestamps use **UTC**
4. Every analysis result includes a **confidence score**
5. Every recommendation must be **explainable**
6. **Decision Engine alone** may generate trading recommendations
7. **Bitunix** = execution validation only — not primary market reference
8. **Binance** = reference exchange for futures market intelligence
9. Every module must support future AI enhancements without redesign
10. Architecture remains **exchange-independent** for long-term scalability

---

### 2.11 Architecture Summary

BTC Analyzer is a modular, evidence-based intelligence platform — not a traditional signal generator. Each layer transforms raw market information into richer insights until the AI Decision Engine synthesizes a Daily Outlook and Intraday Trading Plan. This layered approach ensures robustness, transparency, scalability, and ease of expansion.

---

✅ End of Chapter 2
