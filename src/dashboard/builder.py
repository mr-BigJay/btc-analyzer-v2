"""Assemble canonical DashboardView from analytical payloads (Ch.17)."""

from __future__ import annotations

from typing import Any

from src.dashboard.cards import build_domain_cards
from src.dashboard.colors import bias_tone, connection_tone, msi_tone, risk_tone, severity_tone
from src.dashboard.contracts import DashboardState, DashboardView, Personalization, utc_now_iso
from src.dashboard.explain import build_explainability
from src.dashboard.hierarchy import COMPONENT_LIBRARY, NAVIGATION, PERFORMANCE_TARGETS, build_levels
from src.dashboard.state import resolve_dashboard_state


def build_dashboard_view(
    *,
    ai_report: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
    intelligence: dict[str, Any] | None = None,
    scoring: dict[str, Any] | None = None,
    risk: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
    snapshot: dict[str, Any] | None = None,
    historical: dict[str, Any] | None = None,
    personalization: Personalization | None = None,
    connection_ok: bool = True,
    partial_services: bool = False,
    maintenance: bool = False,
) -> DashboardView:
    ai = dict(ai_report or {})
    analysis = dict(analysis or ai.get("analysis") or {})
    intel = dict(intelligence or ai.get("market_intelligence") or {})
    scoring = dict(scoring or ai.get("scoring") or {})
    risk = dict(risk or ai.get("risk_object") or {})
    snap = dict(snapshot or {})
    prefs = personalization or Personalization()
    events = list(events or [])

    has_payload = bool(ai or scoring or intel or analysis)
    analyzed_at = ai.get("analyzed_at") or scoring.get("scored_at") or intel.get("evaluated_at")
    state = resolve_dashboard_state(
        has_payload=has_payload,
        analyzed_at=analyzed_at,
        connection_ok=connection_ok,
        partial_services=partial_services,
        maintenance=maintenance,
    )

    bias = str(scoring.get("market_bias") or ai.get("market_bias") or analysis.get("market_bias") or "Neutral")
    confidence = float(scoring.get("confidence_score") or ai.get("confidence") or analysis.get("confidence") or 0)
    regime = str(intel.get("market_regime") or ai.get("market_regime") or analysis.get("market_regime") or "—")
    symbol = str(
        ai.get("symbol")
        or scoring.get("symbol")
        or (prefs.favorite_assets[0] if prefs.favorite_assets else "BTCUSDT")
    )
    dqs = scoring.get("data_quality_score")
    crs = risk.get("composite_risk_score")
    scenarios = list(ai.get("scenarios") or [])
    primary = scenarios[0] if scenarios else {"name": ai.get("primary_scenario") or "—"}
    plan = dict(ai.get("trading_plan") or {})

    active_alerts = [e for e in events if not e.get("suppressed")]
    # Filter by personalization severity preference
    sev_order = {"Informational": 0, "Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    min_sev = sev_order.get(prefs.alert_min_severity, 2)
    filtered_alerts = [e for e in active_alerts if sev_order.get(str(e.get("severity")), 0) >= min_sev]

    header = {
        "asset": symbol,
        "timeframe": prefs.preferred_timeframe,
        "market_regime": regime,
        "last_update": analyzed_at or utc_now_iso(),
        "data_quality_score": dqs,
        "connection_status": state,
        "connection_tone": connection_tone(state),
        "active_alerts_count": len(filtered_alerts),
        "fixed": True,
    }

    executive = {
        "market_bias": bias,
        "market_bias_tone": bias_tone(bias),
        "confidence_score": confidence,
        "market_health_index": intel.get("market_health_index"),
        "market_stress_index": intel.get("market_stress_index"),
        "market_stress_tone": msi_tone(str(intel.get("market_stress_index") or "")),
        "composite_risk_score": crs,
        "risk_level": risk.get("risk_level"),
        "risk_tone": risk_tone(risk.get("risk_level") or crs),
        "primary_scenario": primary.get("name") if isinstance(primary, dict) else primary,
        "no_trade_zone": bool(risk.get("no_trade_zone")),
    }

    domain_cards = [c.to_dict() for c in build_domain_cards(analysis=analysis or ai, intelligence=intel, snapshot=snap)]

    reasoning = dict(ai.get("reasoning") or {})
    explain = build_explainability(
        market_bias=bias,
        intelligence=intel,
        scoring=scoring,
        risk=risk,
        reasoning=reasoning,
    ).to_dict()

    narrative = {
        "executive_summary": (ai.get("daily_outlook") or {}).get("executive_summary")
        or reasoning.get("primary_conclusion")
        or "",
        "market_narrative": ai.get("primary_narrative") or "",
        "primary_scenario": primary if isinstance(primary, dict) else {"name": primary},
        "alternative_scenarios": ai.get("alternative_scenarios") or scenarios[1:3],
        "risk_commentary": risk.get("explanation") or reasoning.get("risk_explanation") or "",
        "concise_by_default": True,
        "expandable_reasoning": True,
    }

    alerts_panel = {
        "active_count": len(filtered_alerts),
        "items": [
            {
                "event_id": e.get("event_id"),
                "type": e.get("type"),
                "severity": e.get("severity"),
                "severity_tone": severity_tone(str(e.get("severity") or "")),
                "summary": e.get("summary"),
                "category": e.get("category"),
                "asset": e.get("asset"),
                "state": e.get("state"),
                "timestamp": e.get("timestamp"),
            }
            for e in filtered_alerts[:20]
        ],
        "filters": ["severity", "asset", "category", "time"],
    }

    hist = dict(historical or {})
    if not hist:
        hist = {
            "previous_reports": [],
            "bias_evolution": [],
            "confidence_trend": [],
            "regime_history": [],
            "prediction_outcomes": [],
            "performance_metrics": {},
            "note": "Historical series populated from validation archive when available.",
        }

    levels = build_levels(
        header=header,
        executive=executive,
        domain_cards=domain_cards,
        narrative=narrative,
        trading_plan=plan,
        explainability=explain,
        alerts=alerts_panel,
        historical=hist,
    )

    return DashboardView(
        state=state,
        header=header,
        executive=executive,
        domain_cards=domain_cards,
        narrative=narrative,
        trading_plan=plan,
        explainability=explain,
        alerts=alerts_panel,
        historical=hist,
        navigation=NAVIGATION,
        personalization=prefs.to_dict(),
        performance_targets=PERFORMANCE_TARGETS,
        levels=levels,
        generated_at=utc_now_iso(),
    )


def status_catalog() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "engine_version": "1.0",
        "philosophy": ["Observe", "Understand", "Decide"],
        "information_levels": [
            "Immediate market status",
            "Strategic analysis",
            "Detailed evidence",
            "Historical context",
        ],
        "states": [s.value for s in DashboardState],
        "component_library": COMPONENT_LIBRARY,
        "visualization_standards": {
            "time_series": "Line Chart",
            "volume": "Column Chart",
            "distribution": "Histogram",
            "relative_strength": "Gauge",
            "heat_density": "Heatmap",
            "regime_history": "Timeline",
            "liquidity": "Price Ladder Overlay",
        },
        "semantic_colors": {
            "green": "Bullish / Positive",
            "red": "Bearish / Negative",
            "amber": "Caution",
            "blue": "Informational",
            "gray": "Neutral / Inactive",
        },
        "accessibility": [
            "keyboard_navigation",
            "screen_reader",
            "high_contrast",
            "scalable_typography",
            "color_independent_indicators",
            "reduced_motion",
        ],
        "performance_targets": PERFORMANCE_TARGETS,
        "endpoints": [
            "/api/v1/dashboard/status",
            "/api/v1/dashboard/view",
            "/api/v1/dashboard/preferences",
        ],
    }
