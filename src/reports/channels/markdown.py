"""Markdown export renderer (Ch.10 §10.14 / §10.5)."""

from __future__ import annotations

from typing import Any

from src.reports.audiences import render_for_audience
from src.reports.contracts import Audience, CanonicalReport
from src.reports.localization import labels_for


def render_markdown(
    report: CanonicalReport | dict[str, Any],
    *,
    audience: str = Audience.PROFESSIONAL.value,
    language: str = "en",
) -> str:
    view = render_for_audience(report, audience)
    labels = labels_for(language)
    sections = view.get("sections") or {}
    lines: list[str] = [
        f"# {view.get('report_type')}",
        "",
        f"**Generated:** {view.get('generated_at')}",
        f"**{labels['market_bias']}:** {view.get('market_bias')}  ",
        f"**{labels['confidence']}:** {float(view.get('confidence') or 0):.0f}%  ",
        f"**{labels['regime']}:** {view.get('market_regime')}",
        "",
        "## Executive Summary",
        str(view.get("executive_summary") or ""),
        "",
        "## Key Drivers",
    ]
    for d in view.get("key_drivers") or []:
        lines.append(f"- {d}")

    if sections.get("spot_analysis") or sections.get("futures_analysis"):
        lines += ["", "## Layer Highlights"]
        for key in ("spot_analysis", "futures_analysis", "options_analysis", "technical_analysis", "liquidity_analysis"):
            block = sections.get(key) or {}
            if block:
                lines.append(f"- **{key.replace('_', ' ').title()}:** {block.get('summary') or block}")

    lines += ["", "## Scenarios"]
    primary = view.get("primary_scenario") or {}
    if primary:
        lines.append(f"- **Primary:** {primary.get('name')} ({primary.get('probability')}%)")
    for alt in view.get("alternative_scenarios") or []:
        lines.append(f"- Alt: {alt.get('name')} ({alt.get('probability')}%)")

    plan = view.get("trading_plan") or {}
    lines += [
        "",
        f"## {labels['trading_plan']}",
        f"- Direction: {plan.get('direction')}",
        f"- Entry: {plan.get('preferred_entry_zone')}",
        f"- Targets: {plan.get('targets')}",
        f"- Stop: {plan.get('stop_area')}",
        f"- Size: {plan.get('position_size_recommendation')}",
        "",
        f"## {labels['risk']}",
    ]
    for r in view.get("risk_factors") or []:
        lines.append(f"- {r}")

    explain = view.get("explainability") or {}
    if explain.get("primary_conclusion"):
        lines += ["", "## Explainability", str(explain.get("primary_conclusion"))]

    breakdown = view.get("confidence_breakdown") or []
    if breakdown:
        lines += ["", "## Confidence Breakdown", "| Factor | Impact |", "|---|---|"]
        for row in breakdown:
            lines.append(f"| {row.get('factor')} | {row.get('impact')} |")

    lines += [
        "",
        "## Final Conclusion",
        str(view.get("final_conclusion") or ""),
        "",
        f"*{view.get('disclaimer')}*",
    ]
    meta = view.get("metadata") or {}
    lines += [
        "",
        "---",
        f"Report ID: `{meta.get('report_id')}` · Schema {meta.get('schema_version')} · Engine {meta.get('engine_version')}",
    ]
    return "\n".join(lines)
