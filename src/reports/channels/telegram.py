"""Telegram-optimized rendering (Ch.10 §10.14) — concise, action-oriented."""

from __future__ import annotations

from typing import Any

from src.reports.audiences import render_for_audience
from src.reports.contracts import Audience, CanonicalReport
from src.reports.localization import labels_for


def render_telegram(
    report: CanonicalReport | dict[str, Any],
    *,
    audience: str = Audience.EXECUTIVE.value,
    language: str = "en",
) -> str:
    view = render_for_audience(report, audience)
    labels = labels_for(language)
    bias = view.get("market_bias")
    conf = view.get("confidence")
    regime = view.get("market_regime")
    summary = view.get("executive_summary") or ""
    primary = view.get("primary_scenario") or {}
    plan = view.get("trading_plan") or {}
    risks = view.get("risk_factors") or []

    lines = [
        f"BTC Analyzer — {view.get('report_type')}",
        f"{labels['market_bias']}: {bias}",
        f"{labels['confidence']}: {float(conf or 0):.0f}%",
        f"{labels['regime']}: {regime}",
        "",
        summary,
        "",
        f"{labels['primary_scenario']}: {primary.get('name')} ({primary.get('probability')}%)",
        f"{labels['trading_plan']}: {plan.get('direction')}",
    ]
    if risks:
        lines.append(f"{labels['risk']}: " + "; ".join(str(r) for r in risks[:3]))
    lines.append("")
    lines.append(str(view.get("disclaimer") or ""))
    return "\n".join(lines).strip()
