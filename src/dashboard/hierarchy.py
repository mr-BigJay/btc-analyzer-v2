"""Information hierarchy levels (Ch.17 §17.4)."""

from __future__ import annotations

from typing import Any

from src.dashboard.contracts import InformationLevel


def build_levels(
    *,
    header: dict[str, Any],
    executive: dict[str, Any],
    domain_cards: list[dict[str, Any]],
    narrative: dict[str, Any],
    trading_plan: dict[str, Any],
    explainability: dict[str, Any],
    alerts: dict[str, Any],
    historical: dict[str, Any],
) -> dict[str, Any]:
    return {
        InformationLevel.L1_STATUS.value: {
            "purpose": "Immediate market status",
            "visible_without_scroll_desktop": True,
            "sections": ["header", "executive", "alerts_summary"],
            "header": header,
            "executive": executive,
            "alerts_count": (alerts or {}).get("active_count", 0),
        },
        InformationLevel.L2_STRATEGY.value: {
            "purpose": "Strategic analysis",
            "visible_without_scroll_desktop": True,
            "sections": ["domain_cards", "narrative_summary", "trading_plan"],
            "domain_card_ids": [c.get("id") for c in domain_cards],
            "primary_scenario": (narrative or {}).get("primary_scenario"),
            "trading_plan_direction": (trading_plan or {}).get("preferred_direction"),
        },
        InformationLevel.L3_EVIDENCE.value: {
            "purpose": "Detailed evidence",
            "sections": ["explainability", "alternative_scenarios", "risk_commentary"],
            "explainability": explainability,
            "alternative_scenarios": (narrative or {}).get("alternative_scenarios") or [],
        },
        InformationLevel.L4_HISTORY.value: {
            "purpose": "Historical context",
            "sections": ["historical"],
            "historical": historical,
        },
    }


NAVIGATION = {
    "max_clicks_to_feature": 2,
    "persistent": True,
    "items": [
        {"id": "overview", "label": "Overview", "href": "#overview"},
        {"id": "intelligence", "label": "Intelligence", "href": "#intelligence"},
        {"id": "narrative", "label": "AI Narrative", "href": "#narrative"},
        {"id": "alerts", "label": "Alerts", "href": "#alerts"},
        {"id": "history", "label": "History", "href": "#history"},
        {"id": "risk", "label": "Risk", "href": "#risk"},
    ],
    "shortcuts": {
        "g o": "Overview",
        "g a": "Alerts",
        "g n": "Narrative",
        "g r": "Risk",
        "/": "Asset search",
    },
    "breadcrumbs_root": "Dashboard",
}


PERFORMANCE_TARGETS = {
    "initial_load_ms": 2000,
    "realtime_update_latency_ms": 250,
    "interaction_ms": 100,
    "chart_render_ms": 500,
    "search_response_ms": 200,
}


COMPONENT_LIBRARY = [
    "Metric Card",
    "Score Gauge",
    "Trend Badge",
    "Scenario Card",
    "Risk Indicator",
    "Timeline",
    "Heatmap",
    "Alert Banner",
    "Evidence List",
    "Report Viewer",
]
