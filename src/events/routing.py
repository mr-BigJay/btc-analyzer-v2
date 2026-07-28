"""Notification routing by severity and category (Ch.16 §16.11)."""

from __future__ import annotations

from src.events.contracts import EventObject, EventSeverity, NotificationChannel, SEVERITY_RANK

# Minimum severity (rank) for each channel
CHANNEL_MIN_SEVERITY: dict[str, int] = {
    NotificationChannel.API.value: 0,
    NotificationChannel.DASHBOARD.value: 0,
    NotificationChannel.WEBSOCKET.value: 2,  # Medium+
    NotificationChannel.TELEGRAM.value: 3,  # High+
}


def route_channels(event: EventObject) -> list[str]:
    rank = SEVERITY_RANK.get(event.severity, 0)
    channels: list[str] = []
    for channel, min_rank in CHANNEL_MIN_SEVERITY.items():
        if rank >= min_rank:
            channels.append(channel)
    # System critical always hits all channels
    if event.severity == EventSeverity.CRITICAL.value:
        channels = [
            NotificationChannel.API.value,
            NotificationChannel.DASHBOARD.value,
            NotificationChannel.TELEGRAM.value,
            NotificationChannel.WEBSOCKET.value,
        ]
    # Risk NTZ always dashboard + telegram + ws
    if event.type == "No Trade Zone" and NotificationChannel.TELEGRAM.value not in channels:
        channels.append(NotificationChannel.TELEGRAM.value)
    # Preserve order, unique
    return list(dict.fromkeys(channels))


def assign_routes(events: list[EventObject]) -> list[EventObject]:
    for e in events:
        if e.suppressed:
            e.notification_channels = [NotificationChannel.API.value]  # archived/API only
        else:
            e.notification_channels = route_channels(e)
    return events
