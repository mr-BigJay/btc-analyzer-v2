"""Event correlation — group related signals into higher-level events (Ch.16 §16.8)."""

from __future__ import annotations

from src.events.contracts import (
    EventCategory,
    EventObject,
    EventSeverity,
    EventState,
    SEVERITY_RANK,
    utc_now_iso,
)


# Correlation recipes: member event types → composite label + severity floor
CORRELATION_RECIPES: list[tuple[set[str], str, str]] = [
    (
        {"Funding Extreme", "Open Interest Spike", "Breakout Confirmed"},
        "Potential Short Squeeze",
        EventSeverity.CRITICAL.value,
    ),
    (
        {"Funding Extreme", "Open Interest Spike", "Breakdown Confirmed"},
        "Potential Long Squeeze",
        EventSeverity.CRITICAL.value,
    ),
    (
        {"Funding Extreme", "High Liquidation Event"},
        "Leverage Cascade Risk",
        EventSeverity.CRITICAL.value,
    ),
    (
        {"Liquidity Sweep Detected", "Breakout Confirmed"},
        "Sweep-and-Breakout Continuation",
        EventSeverity.HIGH.value,
    ),
    (
        {"No Trade Zone", "Market Stress Extreme"},
        "Capital Preservation Lockdown",
        EventSeverity.CRITICAL.value,
    ),
    (
        {"Market Regime Change", "Market Bias Change"},
        "Structural Trend Shift",
        EventSeverity.HIGH.value,
    ),
]


def correlate_events(events: list[EventObject]) -> list[EventObject]:
    """Return original events plus any composite correlated events."""
    if len(events) < 2:
        return list(events)

    by_type = {e.type: e for e in events}
    types = set(by_type)
    out = list(events)
    seen_labels: set[str] = set()

    for members, label, sev_floor in CORRELATION_RECIPES:
        if not members.issubset(types):
            continue
        if label in seen_labels:
            continue
        seen_labels.add(label)
        related = [by_type[t] for t in members if t in by_type]
        max_sev = max((SEVERITY_RANK.get(e.severity, 0) for e in related), default=0)
        floor = SEVERITY_RANK.get(sev_floor, 0)
        severity = sev_floor if floor >= max_sev else related[0].severity
        # Prefer higher
        for e in related:
            if SEVERITY_RANK.get(e.severity, 0) > SEVERITY_RANK.get(severity, 0):
                severity = e.severity
        if SEVERITY_RANK.get(severity, 0) < floor:
            severity = sev_floor

        asset = related[0].asset
        composite = EventObject(
            asset=asset,
            category=EventCategory.RISK.value if "Risk" in label or "Squeeze" in label or "Lockdown" in label else related[0].category,
            type=label,
            severity=severity,
            state=EventState.DETECTED.value,
            timestamp=utc_now_iso(),
            summary=f"Correlated: {' + '.join(e.type for e in related)} → {label}.",
            explanation="Correlation reduces alert fatigue by combining related signals.",
            related_events=[e.event_id for e in related],
            correlated=True,
            correlation_label=label,
            related_metrics={"member_types": [e.type for e in related]},
            fingerprint=f"correlated|{label}|{asset}".lower(),
        )
        for e in related:
            if composite.event_id not in e.related_events:
                e.related_events.append(composite.event_id)
            e.correlated = True
            e.correlation_label = label
        out.append(composite)

    return out
