"""Priority assignment and escalation (Ch.16 §16.6 / §16.14)."""

from __future__ import annotations

from src.events.contracts import EventObject, EventSeverity, SEVERITY_RANK, utc_now_iso

ESCALATION_LADDER = [
    EventSeverity.MEDIUM.value,
    EventSeverity.HIGH.value,
    EventSeverity.CRITICAL.value,
]


def assign_priority(event: EventObject) -> EventObject:
    """Normalize / clamp severity; priority is severity rank for routing."""
    if event.severity not in SEVERITY_RANK:
        event.severity = EventSeverity.MEDIUM.value
    return event


def escalate(
    event: EventObject,
    *,
    duration_sec: float = 0,
    recurrence: int = 1,
    market_impact: str = "",
) -> EventObject:
    """Escalate unresolved events based on duration, recurrence, impact."""
    should = False
    if duration_sec >= 3600:
        should = True
    if recurrence >= 3:
        should = True
    if market_impact.lower() in {"high", "extreme", "critical"}:
        should = True
    if not should:
        return event

    rank = SEVERITY_RANK.get(event.severity, 0)
    # Find next rung
    for level in ESCALATION_LADDER:
        if SEVERITY_RANK[level] > rank:
            prev = event.severity
            event.escalated_from = prev
            event.severity = level
            event.notification_history.append(
                {
                    "kind": "escalation",
                    "from": prev,
                    "to": level,
                    "duration_sec": duration_sec,
                    "recurrence": recurrence,
                    "market_impact": market_impact,
                    "at": utc_now_iso(),
                }
            )
            break
    return event
