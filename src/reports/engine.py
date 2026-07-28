"""Report Generation engine (Ch.10).

Formats validated intelligence — does not analyze or score.
"""

from __future__ import annotations

from typing import Any

from src.ai.engine import AIDecisionEngine
from src.cache.keys import CacheKeys
from src.config import settings
from src.events.engine import EventEngine
from src.logging_setup import get_logger
from src.reports.alerts import detect_alerts
from src.reports.audiences import render_for_audience
from src.reports.builder import build_report, build_specialized
from src.reports.channels.export import export_report
from src.reports.channels.markdown import render_markdown
from src.reports.channels.telegram import render_telegram
from src.reports.contracts import Audience, CanonicalReport, ReportType
from src.reports.localization import localize_report_shell
from src.reports.qa import validate_report
from src.storage.redis_cache import redis_cache
from src.storage.repository import CentralRepository

log = get_logger("reports.engine")


class ReportGenerator:
    """Presentation interface (Ch.10 §10.2). Independent of Event Engine delivery."""

    def __init__(self, repository: CentralRepository | None = None) -> None:
        self.repository = repository or CentralRepository()
        self.ai = AIDecisionEngine(self.repository)
        self.event_engine = EventEngine()


    def generate(
        self,
        *,
        report_type: str = ReportType.DAILY_OUTLOOK.value,
        audience: str = Audience.PROFESSIONAL.value,
        language: str = "en",
        timezone: str = "UTC",
        ai_report: dict[str, Any] | None = None,
        persist: bool = True,
        run_upstream_if_missing: bool = True,
        export_formats: list[str] | None = None,
    ) -> dict[str, Any]:
        if ai_report is None:
            if not run_upstream_if_missing:
                cached = redis_cache.get("latest_ai_decision")
                if isinstance(cached, dict):
                    ai_report = cached
                else:
                    raise ValueError("No AI Decision report available for Report Generator")
            else:
                ai_report = self.ai.decide(persist=persist).to_dict()

        decision = ai_report.get("scoring") or redis_cache.get(CacheKeys.LATEST_DECISION_OBJECT) or {}
        intelligence = ai_report.get("market_intelligence") or redis_cache.get(CacheKeys.LATEST_MARKET_INTELLIGENCE) or {}

        if report_type == ReportType.DAILY_OUTLOOK.value:
            report = build_report(
                report_type=report_type,
                ai_report=ai_report,
                decision_object=decision if isinstance(decision, dict) else {},
                intelligence=intelligence if isinstance(intelligence, dict) else {},
                audience=audience,
                language=language,
                timezone=timezone,
            )
        else:
            report = build_specialized(
                report_type,
                ai_report=ai_report,
                decision_object=decision if isinstance(decision, dict) else {},
                intelligence=intelligence if isinstance(intelligence, dict) else {},
                audience=audience,
            )

        qa = validate_report(report)
        report.qa = qa
        report.metadata["published"] = bool(qa.get("publish"))
        payload = localize_report_shell(report.to_dict(), language=language, timezone=timezone)
        payload["qa"] = qa

        alerts = [a.to_dict() for a in detect_alerts(current=payload, symbol=payload.get("metadata", {}).get("symbol", "BTCUSDT"))]
        payload["alerts"] = alerts

        # Ch.16 Event Engine — independent lifecycle (does not replace report QA)
        try:
            event_result = self.event_engine.process_ai_report(
                {
                    **(ai_report or {}),
                    "symbol": payload.get("metadata", {}).get("symbol", "BTCUSDT"),
                    "market_bias": payload.get("market_bias") or (ai_report or {}).get("market_bias"),
                    "confidence": payload.get("confidence") or (ai_report or {}).get("confidence"),
                    "market_regime": payload.get("market_regime") or (ai_report or {}).get("market_regime"),
                    "market_intelligence": intelligence if isinstance(intelligence, dict) else {},
                    "scoring": decision if isinstance(decision, dict) else {},
                    "risk_object": (ai_report or {}).get("risk_object") or {},
                    "evidence": (ai_report or {}).get("evidence") or [],
                },
                persist=persist,
                notify=persist,
                skip_external=True,  # report path still owns Telegram render below
            )
            payload["events"] = event_result.get("active_events") or []
            payload["event_analytics"] = event_result.get("analytics") or {}
            # Prefer Ch.16 event cards when present for dashboard consumers
            if event_result.get("dashboard_cards"):
                payload["event_cards"] = event_result["dashboard_cards"]
        except Exception as exc:  # noqa: BLE001
            log.warning("event engine processing failed: {}", exc)
            payload["events"] = []

        channels = {
            "api": render_for_audience(payload, audience),
            "telegram": render_telegram(payload, audience=Audience.EXECUTIVE.value, language=language),
            "markdown": render_markdown(payload, audience=audience, language=language),
        }
        payload["renders"] = {
            "telegram": channels["telegram"],
            "markdown": channels["markdown"],
        }

        if not qa.get("ok"):
            log.warning("report QA failed errors={}", qa.get("errors"))
            payload["published"] = False
        else:
            payload["published"] = True
            if persist:
                redis_cache.set(CacheKeys.LATEST_REPORT, payload, ttl_sec=86400)
                redis_cache.set(CacheKeys.LATEST_DAILY_OUTLOOK, payload, ttl_sec=86400)
                if export_formats:
                    payload["exports"] = export_report(
                        payload, formats=export_formats, audience=audience, language=language
                    )
                # Best-effort Telegram delivery when configured
                try:
                    from src.notifier import send_telegram

                    send_telegram(channels["telegram"])
                except Exception as exc:  # noqa: BLE001
                    log.debug("telegram delivery skipped: {}", exc)
                # Best-effort websocket / cache alert fan-out
                for alert in alerts:
                    redis_cache.set("latest_alert", alert, ttl_sec=3600)
                for evt in payload.get("events") or []:
                    redis_cache.set(CacheKeys.LATEST_EVENT, evt, ttl_sec=3600)
                    redis_cache.set("latest_alert", evt, ttl_sec=3600)
                try:
                    self.repository.append_report(payload)
                except Exception as exc:  # noqa: BLE001
                    log.warning("reports DB persist failed: {}", exc)
                for alert in alerts:
                    try:
                        self.repository.append_alert(alert)
                    except Exception as exc:  # noqa: BLE001
                        log.warning("alerts DB persist failed: {}", exc)

        log.info(
            "report type={} bias={} conf={} publish={} alerts={} events={}",
            report_type,
            payload.get("market_bias"),
            payload.get("confidence"),
            payload.get("published"),
            len(alerts),
            len(payload.get("events") or []),
        )
        return payload

    def snapshot_report(self, **kwargs: Any) -> dict[str, Any]:
        return self.generate(report_type=ReportType.MARKET_SNAPSHOT.value, **kwargs)

    def trading_plan_report(self, **kwargs: Any) -> dict[str, Any]:
        return self.generate(report_type=ReportType.INTRADAY_PLAN.value, **kwargs)
