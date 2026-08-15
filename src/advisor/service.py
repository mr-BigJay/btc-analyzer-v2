"""Dashboard AI advisor — analyzes live dashboard state and suggests improvements."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.advisor.models import AdvisorInsight
from src.advisor.provider import chat_with_llm, generate_with_llm
from src.advisor.settings_store import is_llm_configured, reload_runtime_settings
from src.analyzer.forecast import ForecastEngine, forecast_to_dict
from src.analyzer.optimize import BacktestOptimizer
from src.analyzer.serialize import analysis_to_dict
from src.analyzer.service import AnalysisService
from src.config import settings
from src.db.models import AdvisorSnapshot, BacktestResult, CollectionLog

logger = logging.getLogger(__name__)


class AdvisorService:
    def __init__(self) -> None:
        self.analysis = AnalysisService()
        self.forecast = ForecastEngine()

    def build_context(self, session: Session) -> dict:
        analysis = self.analysis.analyze(session)
        forecast = self.forecast.build(session, analysis)
        overview = analysis_to_dict(analysis)

        backtests = session.execute(
            select(BacktestResult).order_by(desc(BacktestResult.created_at)).limit(6)
        ).scalars().all()
        bt_by_tf: dict[str, dict] = {}
        for row in backtests:
            if row.timeframe not in bt_by_tf:
                bt_by_tf[row.timeframe] = {
                    "win_rate": row.win_rate,
                    "profit_factor": row.profit_factor,
                    "total_signals": row.total_signals,
                }

        optimized = BacktestOptimizer.get_all_best(session)
        opt_params = {
            tf: {
                "confidence": p.confidence_threshold,
                "min_score_bull": p.min_score_bull,
                "max_score_bear": p.max_score_bear,
                "win_rate": p.win_rate,
                "profit_factor": p.profit_factor,
            }
            for tf, p in optimized.items()
        }

        collection_health = self._collection_health(session)

        return {
            "generated_for": "btc_analyzer_dashboard",
            "overview": {
                "price": overview.get("price"),
                "change_24h_pct": overview.get("change_24h_pct"),
                "overall_score": overview.get("overall_score"),
                "overall_confidence": overview.get("overall_confidence"),
                "summary": overview.get("summary"),
                "mtf_aligned": overview.get("mtf_aligned"),
                "timeframes": {
                    tf: {
                        "trend": overview["timeframes"][tf]["trend"],
                        "score": overview["timeframes"][tf]["score"],
                        "confidence": overview["timeframes"][tf]["confidence"],
                        "levels": overview["timeframes"][tf].get("levels", {}),
                    }
                    for tf in overview.get("timeframes", {})
                },
                "derivatives": overview.get("derivatives"),
                "sentiment": overview.get("sentiment"),
                "onchain": overview.get("onchain"),
                "macro": overview.get("macro"),
                "liquidations": overview.get("liquidations"),
                "coinex": overview.get("coinex"),
                "coinex_ai": overview.get("coinex_ai"),
            },
            "forecast_4h": forecast_to_dict(forecast),
            "backtest": bt_by_tf,
            "optimized_params": opt_params,
            "collection_health": collection_health,
        }

    def _collection_health(self, session: Session) -> dict[str, str]:
        health: dict[str, str] = {}
        rows = session.execute(
            select(CollectionLog).order_by(desc(CollectionLog.finished_at)).limit(50)
        ).scalars().all()
        for row in rows:
            if row.source not in health:
                health[row.source] = row.status
        return health

    def generate_rules(self, context: dict) -> AdvisorInsight:
        ov = context["overview"]
        fc = context["forecast_4h"]
        problems: list[str] = []
        ideas: list[str] = []
        conflicts: list[str] = []
        watch_levels: list[dict] = []

        price = ov.get("price") or 0
        score = ov.get("overall_score") or 50
        confidence = ov.get("overall_confidence") or 0
        tfs = ov.get("timeframes") or {}

        trends = {tf: tfs[tf]["trend"] for tf in tfs}
        bearish_n = sum(1 for t in trends.values() if t == "bearish")
        bullish_n = sum(1 for t in trends.values() if t == "bullish")

        if not ov.get("mtf_aligned"):
            problems.append("تایم‌فریم‌ها هم‌جهت نیستند؛ سیگنال کوتاه‌مدت ضعیف‌تر است.")
        if confidence < 45:
            problems.append(f"اعتماد کلی پایین است ({confidence:.0f}٪) — ورود پرریسک‌تر.")
        if score > 58 and fc.get("direction") == "bearish":
            conflicts.append("امتیاز کلی نسبتاً صعودی است ولی پیش‌بینی ۴ ساعته نزولی است.")
        if score < 42 and fc.get("direction") == "bullish":
            conflicts.append("امتیاز کلی نسبتاً نزولی است ولی پیش‌بینی ۴ ساعته صعودی است.")

        coinex_ai = ov.get("coinex_ai")
        if coinex_ai:
            ai_sig = coinex_ai.get("signal")
            tf4h = trends.get("4h")
            if ai_sig == "bearish" and tf4h == "bullish":
                conflicts.append("CoinEx AI Research نزولی است ولی تایم‌فریم ۴ ساعته صعودی نشان می‌دهد.")
            elif ai_sig == "bullish" and tf4h == "bearish":
                conflicts.append("CoinEx AI Research صعودی است ولی تایم‌فریم ۴ ساعته نزولی نشان می‌دهد.")

        deriv = ov.get("derivatives") or {}
        if deriv.get("funding_signal") == "overleveraged_long" and bullish_n >= 2:
            problems.append("فاندینگ مثبت بالا + تمایل صعودی — احتمال اسکویز نزولی لانگ‌ها.")

        bt = context.get("backtest") or {}
        bt4h = bt.get("4h")
        if bt4h and bt4h.get("profit_factor", 1) < 1:
            problems.append(
                f"بک‌تست ۴ ساعته ضعیف است (PF={bt4h.get('profit_factor', 0):.2f}) — به سیگنال کوتاه‌مدت اعتماد کم کن."
            )

        failed_sources = [
            src for src, status in (context.get("collection_health") or {}).items() if status != "success"
        ]
        if failed_sources:
            problems.append(f"جمع‌آوری داده مشکل دارد: {', '.join(failed_sources[:3])}")

        lv4h = (tfs.get("4h") or {}).get("levels") or {}
        support = lv4h.get("support")
        resistance = lv4h.get("resistance")
        if support:
            watch_levels.append({"price": support, "reason": "حمایت ۴ ساعته"})
        if resistance:
            watch_levels.append({"price": resistance, "reason": "مقاومت ۴ ساعته"})
        if fc.get("primary_target"):
            watch_levels.append({"price": fc["primary_target"], "reason": "هدف پیش‌بینی ۴ ساعته"})
        if fc.get("invalidation"):
            watch_levels.append({"price": fc["invalidation"], "reason": "سطح باطل‌شدن سناریو"})

        if bearish_n >= 2:
            ideas.append("تا شکست مقاومت، پلن دفاعی/شورت روی بازپس‌گیری‌های ضعیف منطقی‌تر است.")
        elif bullish_n >= 2:
            ideas.append("در صورت حفظ حمایت، پلن افزایشی تدریجی با استاپ زیر حمایت بررسی شود.")

        if coinex_ai and coinex_ai.get("summary"):
            ideas.append(f"گزارش CoinEx AI را با سناریوی ۴ ساعته مقایسه کن: {coinex_ai['summary']}")

        risks = fc.get("risks") or []
        if risks:
            ideas.append(f"ریسک اصلی الان: {risks[0]}")

        if not problems:
            problems.append("مشکل بحرانی دیده نشد؛ تمرکز روی مدیریت ریسک و پایبندی به پلن کافی است.")

        headline = "داشبورد نیاز به احتیاط دارد" if conflicts or confidence < 50 else "وضعیت داشبورد قابل پیگیری است"
        confidence_note = (
            f"اعتماد کلی {confidence:.0f}٪ · امتیاز {score:.0f} · پیش‌بینی ۴h: {fc.get('direction_label', '—')}"
        )

        return AdvisorInsight(
            headline=headline,
            problems=problems[:5],
            ideas=ideas[:5],
            conflicts=conflicts[:4],
            watch_levels=watch_levels[:4],
            confidence_note=confidence_note,
            source="rules",
            model="builtin-rules",
        )

    def generate(self, session: Session, force: bool = False) -> AdvisorInsight:
        if not settings.advisor_enabled:
            raise RuntimeError("Advisor is disabled")

        reload_runtime_settings()

        if not force:
            latest = self.get_latest(session)
            if latest and self._is_fresh(latest.generated_at):
                return latest

        context = self.build_context(session)
        try:
            if settings.advisor_api_key:
                insight = generate_with_llm(context)
            else:
                insight = self.generate_rules(context)
        except Exception:
            logger.exception("LLM advisor failed, falling back to rules")
            insight = self.generate_rules(context)

        insight.generated_at = datetime.now(timezone.utc).isoformat()
        self.save(session, insight)
        return insight

    def _is_fresh(self, generated_at: str) -> bool:
        try:
            ts = datetime.fromisoformat(generated_at)
            age_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60
            return age_min < settings.advisor_cache_minutes
        except ValueError:
            return False

    def save(self, session: Session, insight: AdvisorInsight) -> None:
        row = AdvisorSnapshot(
            payload=json.dumps(insight.__dict__, ensure_ascii=False),
            headline=insight.headline,
            source=insight.source,
            model=insight.model,
            created_at=datetime.now(timezone.utc),
        )
        session.add(row)
        session.commit()

    def get_latest(self, session: Session) -> AdvisorInsight | None:
        row = session.execute(
            select(AdvisorSnapshot).order_by(desc(AdvisorSnapshot.created_at)).limit(1)
        ).scalar_one_or_none()
        if not row:
            return None
        data = json.loads(row.payload)
        data["generated_at"] = row.created_at.isoformat()
        return AdvisorInsight(**data)

    def to_dict(self, insight: AdvisorInsight) -> dict:
        return {
            "headline": insight.headline,
            "problems": insight.problems,
            "ideas": insight.ideas,
            "conflicts": insight.conflicts,
            "watch_levels": insight.watch_levels,
            "confidence_note": insight.confidence_note,
            "source": insight.source,
            "model": insight.model,
            "generated_at": insight.generated_at,
            "configured": bool(settings.advisor_api_key),
            "enabled": settings.advisor_enabled,
        }

    def has_actionable_issues(self, insight: AdvisorInsight) -> bool:
        if insight.conflicts:
            return True
        generic_ok = "مشکل بحرانی دیده نشد"
        real_problems = [p for p in insight.problems if generic_ok not in p]
        return bool(real_problems)

    def chat(
        self,
        session: Session,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        if not settings.advisor_enabled:
            raise RuntimeError("Advisor is disabled")

        reload_runtime_settings()
        if not settings.advisor_api_key:
            raise RuntimeError("کلید API تنظیم نشده — از /setkey استفاده کن")

        context = self.build_context(session)
        return chat_with_llm(context, user_message, history)

    def _chat_rules(self, context: dict, user_message: str) -> str:
        insight = self.generate_rules(context)
        msg = user_message.strip().lower()
        lines = [insight.headline, ""]

        if any(k in msg for k in ("مشکل", "ریسک", "خطر", "conflict", "problem")):
            lines.append("مشکلات:")
            for p in insight.problems:
                lines.append(f"• {p}")
            if insight.conflicts:
                lines.append("")
                lines.append("تناقض‌ها:")
                for c in insight.conflicts:
                    lines.append(f"• {c}")
        elif any(k in msg for k in ("ایده", "پیشنهاد", "idea", "چیکار", "چه کار")):
            lines.append("ایده‌ها:")
            for idea in insight.ideas:
                lines.append(f"• {idea}")
        elif any(k in msg for k in ("سطح", "قیمت", "level", "حمایت", "مقاومت")):
            if insight.watch_levels:
                lines.append("سطوح کلیدی:")
                for lv in insight.watch_levels:
                    price = lv.get("price")
                    reason = lv.get("reason", "")
                    if price:
                        lines.append(f"• ${price:,.0f} — {reason}")
            else:
                lines.append("سطح مشخصی در داده فعلی نیست.")
        else:
            lines.append(insight.confidence_note)
            lines.append("")
            lines.append("مشکلات:")
            for p in insight.problems[:3]:
                lines.append(f"• {p}")
            if insight.conflicts:
                lines.append("")
                lines.append("تناقض:")
                lines.append(f"• {insight.conflicts[0]}")
            lines.append("")
            lines.append("می‌تونی بپرسی: «مشکلات چیه؟»، «ایده‌ها»، «سطوح کلیدی»")

        lines.append("")
        if is_llm_configured():
            lines.append("(خطا در اتصال هوش مصنوعی — دوباره امتحان کن یا تنظیمات API را بررسی کن)")
        else:
            lines.append(
                "⚠️ حالت ساده فعال است.\n"
                "از داشبورد → بخش «۰ · ستاپ ایجنت» → کلید API را وارد کن → ذخیره.\n"
                "یا در تلگرام: /setkey کلید-تو"
            )
        return "\n".join(lines)
