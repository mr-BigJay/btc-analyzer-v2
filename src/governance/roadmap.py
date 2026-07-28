"""Roadmap, plugins, assets, maturity, feedback, debt (Ch.23)."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any

from src.config import settings
from src.governance.contracts import (
    ARCHITECTURAL_SEPARATIONS,
    DOCUMENTATION_UPDATES,
    FEEDBACK_DRIVERS,
    FUTURE_ASSETS,
    GOVERNANCE_LIFECYCLE,
    KNOWLEDGE_ARTIFACTS,
    LONG_TERM_ARCHITECTURE_PRINCIPLES,
    MATURITY_MODEL,
    PLUGIN_CATEGORIES,
    ROADMAP,
    STRATEGIC_PRINCIPLES,
    SUCCESS_METRICS,
    TECH_DEBT_GUIDELINES,
    ENDURING_PRINCIPLES,
    MaturityStage,
    utc_now_iso,
)


def roadmap_view() -> dict[str, Any]:
    return {
        "vision": [
            "Aggregate multi-layer market intelligence",
            "Generate explainable AI-driven market analysis",
            "Support institutional-grade decision making",
            "Scale across multiple asset classes",
            "Provide extensible analytical services through APIs",
        ],
        "strategic_principles": STRATEGIC_PRINCIPLES,
        "versions": ROADMAP,
        "current": "1.0",
        "next": "1.5",
        "timestamp": utc_now_iso(),
    }


def plugin_architecture() -> dict[str, Any]:
    return {
        "status": "planned",
        "categories": PLUGIN_CATEGORIES,
        "interface_rule": "Plugins communicate only through documented interfaces",
        "installable": True,
        "timestamp": utc_now_iso(),
    }


def asset_expansion() -> dict[str, Any]:
    current = [s.strip() for s in (settings.supported_assets or "BTCUSDT").split(",") if s.strip()]
    return {
        "current_assets": current,
        "future_asset_classes": FUTURE_ASSETS,
        "architecture": "asset-independent",
        "timestamp": utc_now_iso(),
    }


def maturity_status(*, stage: str | None = None) -> dict[str, Any]:
    current = stage or MaturityStage.OPERATIONAL.value
    return {
        "current_stage": current,
        "model": MATURITY_MODEL,
        "path": list(MATURITY_MODEL.keys()),
        "timestamp": utc_now_iso(),
    }


def knowledge_base_catalog() -> dict[str, Any]:
    return {
        "artifacts": KNOWLEDGE_ARTIFACTS,
        "versioned": True,
        "reviewable": True,
        "timestamp": utc_now_iso(),
    }


def feedback_loop() -> dict[str, Any]:
    return {
        "drivers": FEEDBACK_DRIVERS,
        "decision_style": "evidence-based",
        "timestamp": utc_now_iso(),
    }


def governance_lifecycle() -> dict[str, Any]:
    return {
        "stages": GOVERNANCE_LIFECYCLE,
        "applies_to": "every significant architectural change",
        "bypass_forbidden": True,
        "timestamp": utc_now_iso(),
    }


def documentation_policy() -> dict[str, Any]:
    return {
        "required_updates": DOCUMENTATION_UPDATES,
        "evolves_with_platform": True,
        "timestamp": utc_now_iso(),
    }


class TechDebtRegistry:
    def __init__(self, maxlen: int = 200) -> None:
        self._lock = threading.Lock()
        self._items: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def record(self, *, title: str, risk: str = "medium", area: str = "architecture") -> dict[str, Any]:
        row = {
            "debt_id": f"TD-{len(self._items)+1}",
            "title": title,
            "risk": risk,
            "area": area,
            "status": "open",
            "recorded_at": utc_now_iso(),
        }
        with self._lock:
            self._items.append(row)
        return row

    def list(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(reversed(self._items))[:limit]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


tech_debt_registry = TechDebtRegistry()


def tech_debt_status() -> dict[str, Any]:
    return {
        "guidelines": TECH_DEBT_GUIDELINES,
        "items": tech_debt_registry.list(),
        "open_count": len(tech_debt_registry.list(limit=500)),
        "timestamp": utc_now_iso(),
    }


def success_metrics() -> dict[str, Any]:
    return {
        "metrics": SUCCESS_METRICS,
        "review_cadence": "periodic",
        "timestamp": utc_now_iso(),
    }


def architectural_statement() -> dict[str, Any]:
    return {
        "statement": (
            "BTC Analyzer is designed as a modular, explainable, AI-assisted market intelligence platform."
        ),
        "separations": ARCHITECTURAL_SEPARATIONS,
        "long_term_principles": LONG_TERM_ARCHITECTURE_PRINCIPLES,
        "enduring_principles": ENDURING_PRINCIPLES,
        "timestamp": utc_now_iso(),
    }
