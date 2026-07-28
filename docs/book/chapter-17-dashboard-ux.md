# BTC Analyzer Enterprise Design Book
## Chapter 17 — Dashboard, Visualization & User Experience
**Version:** 1.0

> Present intelligence, not raw data. Observe → Understand → Decide. Presentation never mutates analytical results.

---

### 17.1 Purpose

Reduce cognitive load while maximizing situational awareness through a clear, responsive, explainable interface.

### 17.2 Information Hierarchy

| Level | Purpose | Desktop |
|-------|---------|---------|
| 1 | Immediate market status | Visible without scroll |
| 2 | Strategic analysis | Visible without scroll |
| 3 | Detailed evidence | Progressive disclosure |
| 4 | Historical context | Below fold |

### 17.3 Package Mapping

| Spec | Code |
|------|------|
| View contracts / personalization | `src/dashboard/contracts.py` |
| Domain cards / explainability | `src/dashboard/cards.py`, `explain.py` |
| State model / colors / hierarchy | `src/dashboard/state.py`, `colors.py`, `hierarchy.py` |
| Builder / engine | `src/dashboard/builder.py`, `engine.py` |
| Service / API | `src/services/dashboard.py`, `/api/v1/dashboard/*` |
| UI shell | `frontend/index.html`, `css/style.css`, `js/dashboard.js` |

### 17.4 Operational States

Loading · Live · Stale · Degraded · Offline · Maintenance

### 17.5 Design Principles

Intelligence before raw data · Progressive disclosure · Explainability · Semantic colors with labels · Responsive & accessible · Presentation independent from analytics
