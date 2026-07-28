"""Dashboard Engine (Ch.17) — presentation aggregation, no analytical mutation."""

from __future__ import annotations

from typing import Any

from src.cache.keys import CacheKeys
from src.dashboard.builder import build_dashboard_view, status_catalog
from src.dashboard.contracts import Personalization
from src.logging_setup import get_logger
from src.storage.redis_cache import redis_cache

log = get_logger("dashboard.engine")

PREFS_KEY = "dashboard:personalization"


class DashboardEngine:
    """Assembles UX view models from cached analytical outputs."""

    def get_preferences(self) -> Personalization:
        raw = redis_cache.get(PREFS_KEY)
        return Personalization.from_dict(raw if isinstance(raw, dict) else None)

    def set_preferences(self, data: dict[str, Any]) -> Personalization:
        current = self.get_preferences().to_dict()
        current.update({k: v for k, v in data.items() if v is not None})
        prefs = Personalization.from_dict(current)
        redis_cache.set(PREFS_KEY, prefs.to_dict(), ttl_sec=86400 * 30)
        return prefs

    def build_view(
        self,
        *,
        ai_report: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        intelligence: dict[str, Any] | None = None,
        scoring: dict[str, Any] | None = None,
        risk: dict[str, Any] | None = None,
        events: list[dict[str, Any]] | None = None,
        snapshot: dict[str, Any] | None = None,
        historical: dict[str, Any] | None = None,
        connection_ok: bool = True,
        partial_services: bool = False,
        maintenance: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        if use_cache:
            ai_report = ai_report or _as_dict(redis_cache.get("latest_ai_decision"))
            intelligence = intelligence or _as_dict(redis_cache.get(CacheKeys.LATEST_MARKET_INTELLIGENCE))
            scoring = scoring or _as_dict(redis_cache.get(CacheKeys.LATEST_DECISION_OBJECT))
            risk = risk or _as_dict(redis_cache.get(CacheKeys.LATEST_RISK_OBJECT))
            analysis = analysis or _as_dict(redis_cache.get("latest_market_analysis"))
            if events is None:
                events = _events_from_cache()
            if snapshot is None:
                snapshot = {
                    "mark_price": redis_cache.get(CacheKeys.LATEST_MARK_PRICE),
                    "funding_rate": redis_cache.get(CacheKeys.LATEST_FUNDING_RATE),
                    "open_interest": redis_cache.get(CacheKeys.CURRENT_OPEN_INTEREST),
                }
            if historical is None:
                historical = _historical_from_validation()

        prefs = self.get_preferences()
        view = build_dashboard_view(
            ai_report=ai_report,
            analysis=analysis,
            intelligence=intelligence,
            scoring=scoring,
            risk=risk,
            events=events,
            snapshot=snapshot,
            historical=historical,
            personalization=prefs,
            connection_ok=connection_ok,
            partial_services=partial_services,
            maintenance=maintenance,
        )
        payload = view.to_dict()
        payload["component_library"] = status_catalog()["component_library"]
        redis_cache.set("latest_dashboard_view", payload, ttl_sec=120)
        log.info("dashboard view state={} bias={}", view.state, view.executive.get("market_bias"))
        return payload

    def status(self) -> dict[str, Any]:
        return status_catalog()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _events_from_cache() -> list[dict[str, Any]]:
    try:
        from src.events.archive import event_archive

        return event_archive.list(limit=30)
    except Exception:  # noqa: BLE001
        return []


def _historical_from_validation() -> dict[str, Any]:
    try:
        from src.validation.archive import prediction_archive

        preds = prediction_archive.list(limit=20)
        bias_evolution = [{"t": p.get("created_at") or p.get("timestamp"), "bias": p.get("market_bias")} for p in preds]
        confidence_trend = [
            {"t": p.get("created_at") or p.get("timestamp"), "confidence": p.get("confidence")} for p in preds
        ]
        return {
            "previous_reports": preds[:10],
            "bias_evolution": bias_evolution,
            "confidence_trend": confidence_trend,
            "regime_history": [{"t": p.get("created_at"), "regime": p.get("market_regime")} for p in preds],
            "prediction_outcomes": preds[:10],
            "performance_metrics": {},
        }
    except Exception:  # noqa: BLE001
        return {
            "previous_reports": [],
            "bias_evolution": [],
            "confidence_trend": [],
            "regime_history": [],
            "prediction_outcomes": [],
            "performance_metrics": {},
        }
