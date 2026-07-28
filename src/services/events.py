"""Event / alerting service facade (Ch.16)."""

from __future__ import annotations

from typing import Any

from src.events.contracts import EVENT_ENGINE_VERSION, EVENT_SCHEMA_VERSION
from src.events.engine import EventEngine
from src.events.formatters import dashboard_event_card, format_telegram_alert
from src.events.contracts import EventObject


class EventService:
    def __init__(self) -> None:
        self.engine = EventEngine()

    def process(self, snapshot: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        asset = str(kwargs.pop("asset", None) or snapshot.get("symbol") or "BTCUSDT")
        return self.engine.process_snapshot(current=snapshot, asset=asset, **kwargs)

    def process_ai_report(self, report: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self.engine.process_ai_report(report, **kwargs)

    def system_alert(self, **kwargs: Any) -> dict[str, Any]:
        return self.engine.ingest_system_event(**kwargs)

    def list_events(self, **filters: Any) -> list[dict[str, Any]]:
        return self.engine.list_events(**filters)

    def resolve(self, event_id: str) -> dict[str, Any] | None:
        return self.engine.resolve(event_id)

    def analytics(self) -> dict[str, Any]:
        return self.engine.analytics()

    def replay(self, snapshots: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        return self.engine.replay(snapshots, **kwargs)

    def dashboard_cards(self, *, limit: int = 30) -> list[dict[str, Any]]:
        rows = self.engine.list_events(limit=limit)
        cards = []
        for row in rows:
            if row.get("suppressed"):
                continue
            cards.append(dashboard_event_card(EventObject.from_dict(row)))
        return cards

    def format_telegram(self, event: dict[str, Any]) -> str:
        return format_telegram_alert(EventObject.from_dict(event))

    def status(self) -> dict[str, Any]:
        analytics = self.analytics()
        return {
            "schema_version": EVENT_SCHEMA_VERSION,
            "engine_version": EVENT_ENGINE_VERSION,
            "lifecycle": [
                "Detection",
                "Validation",
                "Classification",
                "Correlation",
                "Deduplication",
                "Priority Assignment",
                "Notification",
                "Archive",
            ],
            "categories": [
                "Price",
                "Trend",
                "Futures",
                "Options",
                "Liquidity",
                "Risk",
                "System",
                "Macro",
            ],
            "severities": ["Informational", "Low", "Medium", "High", "Critical"],
            "channels": ["API", "Dashboard", "Telegram", "WebSocket"],
            "analytics": analytics,
            "governance": [
                "event_driven",
                "deterministic_rules",
                "no_bypass_validation",
                "immutable_archive",
                "critical_bypasses_rate_limits",
            ],
        }
