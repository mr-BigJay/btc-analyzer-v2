"""Telegram + dashboard presentation from EventObject (Ch.16 §16.12–§16.13)."""

from __future__ import annotations

from typing import Any

from src.events.contracts import EventObject, SEVERITY_RANK

SEVERITY_ICON = {
    "Informational": "ℹ️",
    "Low": "▫️",
    "Medium": "⚠️",
    "High": "🚨",
    "Critical": "🔴",
}


def format_telegram_alert(event: EventObject) -> str:
    icon = SEVERITY_ICON.get(event.severity, "🔔")
    lines = [
        f"{icon} {event.type}",
        "",
        f"Asset:\n{event.asset}",
        "",
        f"Severity:\n{event.severity}",
        "",
        f"Summary:\n{event.summary}",
    ]
    metrics = event.related_metrics or {}
    if metrics.get("confidence") is not None:
        lines.extend(["", f"Confidence:\n{float(metrics['confidence']):.0f}%"])
    if event.trigger_conditions.get("from") and event.trigger_conditions.get("to"):
        lines.extend(
            [
                "",
                f"Previous:\n{event.trigger_conditions['from']}",
                "",
                f"Current:\n{event.trigger_conditions['to']}",
            ]
        )
    if event.explanation:
        lines.extend(["", f"Primary Driver:\n{event.explanation[:200]}"])
    if event.correlation_label:
        lines.extend(["", f"Correlated:\n{event.correlation_label}"])
    return "\n".join(lines)


def dashboard_event_card(event: EventObject) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "severity": event.severity,
        "severity_rank": SEVERITY_RANK.get(event.severity, 0),
        "timestamp": event.timestamp,
        "asset": event.asset,
        "category": event.category,
        "type": event.type,
        "summary": event.summary,
        "explanation": event.explanation,
        "supporting_metrics": event.related_metrics,
        "related_events": list(event.related_events),
        "state": event.state,
        "suppressed": event.suppressed,
        "channels": list(event.notification_channels),
    }
