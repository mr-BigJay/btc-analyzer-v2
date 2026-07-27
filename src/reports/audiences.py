"""Audience-specific views (Ch.10 §10.4) — never alter analytical values."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.reports.contracts import Audience, CanonicalReport


def render_for_audience(report: CanonicalReport | dict[str, Any], audience: str) -> dict[str, Any]:
    data = report.to_dict() if isinstance(report, CanonicalReport) else deepcopy(report)
    data.setdefault("metadata", {})["audience"] = audience

    if audience == Audience.EXECUTIVE.value:
        return {
            "report_type": data.get("report_type"),
            "generated_at": data.get("generated_at"),
            "market_bias": data.get("market_bias"),
            "confidence": data.get("confidence"),
            "market_regime": data.get("market_regime"),
            "executive_summary": data.get("executive_summary"),
            "primary_scenario": {
                "name": (data.get("primary_scenario") or {}).get("name"),
                "probability": (data.get("primary_scenario") or {}).get("probability"),
            },
            "trading_plan": {
                "direction": (data.get("trading_plan") or {}).get("direction"),
            },
            "risk_factors": (data.get("risk_factors") or [])[:3],
            "final_conclusion": data.get("final_conclusion"),
            "disclaimer": data.get("disclaimer"),
            "metadata": data.get("metadata"),
            "qa": data.get("qa"),
        }

    if audience == Audience.PROFESSIONAL.value:
        # Reasoning, scenarios, risk, technical confirmation — omit raw composites
        view = deepcopy(data)
        view.pop("decision_object", None)
        view.pop("ai_report", None)
        # Keep intelligence high-level only
        intel = view.get("market_intelligence") or {}
        view["market_intelligence"] = {
            k: intel.get(k)
            for k in (
                "market_regime",
                "market_cycle",
                "dominant_participant",
                "market_health_index",
                "market_stress_index",
                "liquidity_state",
                "derivatives_thesis",
            )
            if k in intel
        }
        return view

    # Analyst — full report including raw metrics / layer scores / composites
    return data
