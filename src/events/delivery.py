"""Delivery status tracking and retries (Ch.16 §16.17)."""

from __future__ import annotations

from typing import Any, Callable

from src.events.contracts import DeliveryRecord, DeliveryStatus, EventObject, NotificationChannel, utc_now_iso
from src.logging_setup import get_logger

log = get_logger("events.delivery")

MAX_RETRIES = 2


def deliver_event(
    event: EventObject,
    *,
    telegram_sender: Callable[[str], bool] | None = None,
    websocket_publisher: Callable[[dict[str, Any]], None] | None = None,
    db_appender: Callable[[dict[str, Any]], None] | None = None,
    skip_external: bool = False,
) -> EventObject:
    """Attempt delivery on assigned channels; record status. Idempotent per channel attempt log."""
    if event.suppressed:
        event.notification_history.append(
            DeliveryRecord(
                channel="*",
                status=DeliveryStatus.SUPPRESSED.value,
            ).to_dict()
        )
        return event

    from src.events.formatters import format_telegram_alert

    for channel in event.notification_channels:
        record = DeliveryRecord(channel=channel, status=DeliveryStatus.QUEUED.value)
        try:
            if channel == NotificationChannel.TELEGRAM.value and not skip_external:
                sender = telegram_sender
                if sender is None:
                    from src.notifier import send_telegram

                    sender = send_telegram
                text = format_telegram_alert(event)
                ok = bool(sender(text))
                record.attempts = 1
                record.status = DeliveryStatus.SENT.value if ok else DeliveryStatus.FAILED.value
                if not ok:
                    # Retry once
                    for attempt in range(MAX_RETRIES):
                        record.attempts += 1
                        record.status = DeliveryStatus.RETRIED.value
                        if sender(text):
                            record.status = DeliveryStatus.SENT.value
                            break
                    if record.status != DeliveryStatus.SENT.value:
                        record.status = DeliveryStatus.FAILED.value
                        record.last_error = "telegram delivery failed"
            elif channel == NotificationChannel.WEBSOCKET.value and not skip_external:
                pub = websocket_publisher
                if pub is None:
                    pub = _sync_ws_publish
                pub(event.to_dict())
                record.attempts = 1
                record.status = DeliveryStatus.SENT.value
            elif channel in (NotificationChannel.API.value, NotificationChannel.DASHBOARD.value):
                record.attempts = 1
                record.status = DeliveryStatus.DELIVERED.value
            else:
                record.attempts = 1
                record.status = DeliveryStatus.DELIVERED.value
        except Exception as exc:  # noqa: BLE001
            record.status = DeliveryStatus.FAILED.value
            record.last_error = str(exc)
            log.warning("delivery failed channel={} err={}", channel, exc)
        record.updated_at = utc_now_iso()
        event.notification_history.append(record.to_dict())

    if db_appender is not None:
        try:
            db_appender(_to_alert_row(event))
        except Exception as exc:  # noqa: BLE001
            log.warning("db alert append failed: {}", exc)
            event.notification_history.append(
                DeliveryRecord(channel="DB", status=DeliveryStatus.FAILED.value, last_error=str(exc)).to_dict()
            )

    return event


def _sync_ws_publish(alert: dict[str, Any]) -> None:
    """Best-effort: cache for WS clients; async hub used when loop available."""
    from src.cache.keys import CacheKeys
    from src.storage.redis_cache import redis_cache

    redis_cache.set("latest_alert", alert, ttl_sec=3600)
    redis_cache.set(CacheKeys.WS_BROADCAST, {"type": "alert", "data": alert}, ttl_sec=60)
    try:
        import asyncio

        from src.websocket import hub

        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(hub.publish_alert(alert))
        else:
            loop.run_until_complete(hub.publish_alert(alert))
    except Exception:  # noqa: BLE001
        # No running loop / hub unavailable — cache-only fan-out is enough
        pass


def _to_alert_row(event: EventObject) -> dict[str, Any]:
    return {
        "alert_type": event.type,
        "severity": event.severity.lower() if event.severity else "info",
        "message": event.summary,
        "symbol": event.asset,
        "timestamp": event.timestamp,
        "delivered": any(
            h.get("status") in (DeliveryStatus.SENT.value, DeliveryStatus.DELIVERED.value)
            for h in event.notification_history
            if isinstance(h, dict) and h.get("kind") != "state_transition"
        ),
        "payload": event.to_dict(),
    }
