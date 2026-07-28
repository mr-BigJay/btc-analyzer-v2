"""Event Processing Engine (Ch.16) — detection → archive lifecycle."""

from __future__ import annotations

from typing import Any

from src.events.archive import EventArchive, event_archive
from src.events.analytics import compute_analytics
from src.events.contracts import EVENT_ENGINE_VERSION, EVENT_SCHEMA_VERSION, EventObject, EventState
from src.events.correlation import correlate_events
from src.events.dedupe import apply_deduplication
from src.events.delivery import deliver_event
from src.events.detection import detect_events
from src.events.formatters import dashboard_event_card, format_telegram_alert
from src.events.priority import assign_priority, escalate
from src.events.rate_limit import apply_rate_limits
from src.events.routing import assign_routes
from src.logging_setup import get_logger
from src.storage.redis_cache import redis_cache

log = get_logger("events.engine")

PREV_SNAPSHOT_KEY = "events:previous_snapshot"


class EventEngine:
    """Independent event-driven alerting layer — not schedule-driven."""

    def __init__(self, archive: EventArchive | None = None) -> None:
        self.archive = archive or event_archive

    def process_snapshot(
        self,
        *,
        current: dict[str, Any],
        previous: dict[str, Any] | None = None,
        asset: str = "BTCUSDT",
        system: dict[str, Any] | None = None,
        persist: bool = True,
        notify: bool = True,
        skip_external: bool = False,
        escalate_unresolved: bool = False,
    ) -> dict[str, Any]:
        """Full lifecycle: detect → validate → classify → correlate → dedupe → priority → notify → archive."""
        prev = previous
        if prev is None:
            cached = redis_cache.get(PREV_SNAPSHOT_KEY)
            prev = cached if isinstance(cached, dict) else {}

        # 1 Detection
        raw = detect_events(current=current, previous=prev, asset=asset, system=system)

        # 2 Validation — every event must have type, category, severity, fingerprint
        validated = [e for e in raw if self._validate(e)]

        # 3 Classification already on EventObject (category/severity from rules)
        for e in validated:
            assign_priority(e)
            e.transition(EventState.CONFIRMED.value)

        # 4 Correlation
        correlated = correlate_events(validated)

        # 5 Deduplication
        deduped = apply_deduplication(correlated, persist=persist)

        # 6 Priority / optional escalation for recurring unresolved
        if escalate_unresolved:
            for e in deduped:
                if not e.suppressed:
                    escalate(e, recurrence=1, market_impact=e.severity)

        # 7 Routing
        routed = assign_routes(deduped)

        # Rate limiting (critical bypasses)
        limited = apply_rate_limits(routed, persist=persist)

        # 8 Notification
        notified: list[EventObject] = []
        db_appender = None
        if persist and notify:
            db_appender = self._db_appender()

        for event in limited:
            if notify and not event.suppressed:
                deliver_event(
                    event,
                    db_appender=db_appender,
                    skip_external=skip_external,
                )
                event.transition(EventState.ACTIVE.value)
            elif event.suppressed:
                deliver_event(event, skip_external=True)  # records suppressed
            notified.append(event)

            # 9 Archive (all events, including suppressed — auditability)
            if persist:
                self.archive.append(event, persist=True)

        if persist:
            # Store slim previous snapshot for next detection cycle
            redis_cache.set(
                PREV_SNAPSHOT_KEY,
                {
                    "market_regime": current.get("market_regime")
                    or (current.get("market_intelligence") or {}).get("market_regime"),
                    "confidence": current.get("confidence")
                    or (current.get("scoring") or {}).get("confidence_score"),
                    "market_bias": current.get("market_bias"),
                    "volatility": (current.get("market_intelligence") or {}).get("volatility_regime")
                    or current.get("volatility"),
                    "market_intelligence": {
                        "liquidity_state": (current.get("market_intelligence") or {}).get("liquidity_state"),
                        "derivatives_thesis": (current.get("market_intelligence") or {}).get("derivatives_thesis"),
                        "volatility_regime": (current.get("market_intelligence") or {}).get("volatility_regime"),
                        "market_stress_index": (current.get("market_intelligence") or {}).get("market_stress_index"),
                        "market_regime": (current.get("market_intelligence") or {}).get("market_regime"),
                    },
                },
                ttl_sec=86400,
            )

        active = [e for e in notified if not e.suppressed]
        cards = [dashboard_event_card(e) for e in active]
        analytics = compute_analytics([e.to_dict() for e in notified])

        log.info(
            "events processed detected={} active={} suppressed={} correlated={}",
            len(raw),
            len(active),
            sum(1 for e in notified if e.suppressed),
            sum(1 for e in notified if e.correlated and e.type not in {x.type for x in validated}),
        )

        return {
            "events": [e.to_dict() for e in notified],
            "active_events": [e.to_dict() for e in active],
            "dashboard_cards": cards,
            "analytics": analytics,
            "schema_version": EVENT_SCHEMA_VERSION,
            "engine_version": EVENT_ENGINE_VERSION,
        }

    def process_ai_report(
        self,
        report: dict[str, Any],
        *,
        persist: bool = True,
        notify: bool = True,
        skip_external: bool = False,
    ) -> dict[str, Any]:
        asset = str(report.get("symbol") or "BTCUSDT")
        current = {
            "market_bias": report.get("market_bias"),
            "confidence": report.get("confidence"),
            "market_regime": report.get("market_regime"),
            "market_intelligence": report.get("market_intelligence") or {},
            "scoring": report.get("scoring") or {},
            "risk_object": report.get("risk_object") or {},
            "evidence": report.get("evidence") or [],
            "macro_event": (report.get("market_intelligence") or {}).get("macro_event"),
        }
        return self.process_snapshot(
            current=current,
            asset=asset,
            persist=persist,
            notify=notify,
            skip_external=skip_external,
        )

    def ingest_system_event(
        self,
        *,
        asset: str = "BTCUSDT",
        collector_failure: bool = False,
        exchange_degraded: bool = False,
        message: str = "",
        persist: bool = True,
        notify: bool = True,
        skip_external: bool = False,
    ) -> dict[str, Any]:
        return self.process_snapshot(
            current={},
            previous={},
            asset=asset,
            system={
                "collector_failure": collector_failure,
                "exchange_degraded": exchange_degraded,
                "message": message,
            },
            persist=persist,
            notify=notify,
            skip_external=skip_external,
        )

    def list_events(self, **filters: Any) -> list[dict[str, Any]]:
        return self.archive.list(**filters)

    def resolve(self, event_id: str) -> dict[str, Any] | None:
        return self.archive.resolve(event_id)

    def analytics(self) -> dict[str, Any]:
        return compute_analytics(self.archive.list(limit=500))

    def replay(self, snapshots: list[dict[str, Any]], *, asset: str = "BTCUSDT") -> dict[str, Any]:
        """Replay historical snapshots after recovery (idempotent via dedupe)."""
        all_events: list[dict[str, Any]] = []
        prev: dict[str, Any] | None = None
        for snap in snapshots:
            result = self.process_snapshot(
                current=snap,
                previous=prev,
                asset=asset,
                persist=True,
                notify=False,
                skip_external=True,
            )
            all_events.extend(result.get("events") or [])
            prev = snap
        return {"replayed": len(snapshots), "events": all_events, "analytics": compute_analytics(all_events)}

    @staticmethod
    def _validate(event: EventObject) -> bool:
        if not event.type or not event.category or not event.severity:
            return False
        if not event.fingerprint:
            event.fingerprint = f"{event.category}|{event.type}|{event.asset}".lower()
        if not event.summary:
            event.summary = event.type
        return True

    @staticmethod
    def _db_appender():
        try:
            from src.storage.repository import CentralRepository

            repo = CentralRepository()

            def _append(row: dict[str, Any]) -> None:
                repo.append_alert(row)

            return _append
        except Exception:  # noqa: BLE001
            return None


def format_event_telegram(event: EventObject | dict[str, Any]) -> str:
    if isinstance(event, dict):
        event = EventObject.from_dict(event)
    return format_telegram_alert(event)
