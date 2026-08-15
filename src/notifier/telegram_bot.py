import logging

from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.advisor.agent_tasks import create_task, format_task_summary, list_tasks
from src.advisor.service import AdvisorService
from src.advisor.settings_store import is_llm_configured, reload_runtime_settings, set_api_key, to_public_dict
from src.analyzer.forecast import ForecastEngine
from src.analyzer.service import AnalysisService
from src.config import settings
from src.db.models import get_session, init_db
from src.notifier.formatters import (
    advisor_alert_message,
    advisor_message,
    forecast_4h_message,
    overview_message,
    timeframe_message,
)

logger = logging.getLogger(__name__)

CHAT_HISTORY_KEY = "advisor_history"


class TelegramBotService:
    def __init__(self) -> None:
        self.analysis = AnalysisService()
        self.forecast = ForecastEngine()
        self.advisor = AdvisorService()
        self._app: Application | None = None
        self._bot: Bot | None = None

    def _get_bot(self) -> Bot:
        if not settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
        if self._bot is None:
            self._bot = Bot(token=settings.telegram_bot_token)
        return self._bot

    def _allowed(self, update: Update) -> bool:
        if not settings.telegram_chat_id:
            return True
        chat_id = str(update.effective_chat.id)
        allowed = settings.telegram_chat_id.split(",")
        return chat_id in allowed

    async def _deny(self, update: Update) -> None:
        if update.message:
            await update.message.reply_text("دسترسی مجاز نیست.")

    def _get_history(self, context: ContextTypes.DEFAULT_TYPE) -> list[dict[str, str]]:
        return context.chat_data.setdefault(CHAT_HISTORY_KEY, [])

    def _append_history(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        role: str,
        content: str,
    ) -> None:
        history = self._get_history(context)
        history.append({"role": role, "content": content})
        limit = settings.advisor_chat_history_limit
        if len(history) > limit:
            del history[: len(history) - limit]

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        await update.message.reply_text(
            "سلام! من ربات تحلیل BTC هستم.\n\n"
            "دستورات:\n"
            "/status — خلاصه بازار\n"
            "/4h — پیش‌بینی ۴ ساعت آینده\n"
            "/1d — تحلیل روزانه\n"
            "/1w — تحلیل هفتگی\n"
            "/advisor — تحلیل مشاور هوش مصنوعی\n"
            "/config — وضعیت اتصال AI\n"
            "/setkey — تنظیم API Key از تلگرام\n"
            "/agent — ارسال درخواست اصلاح به Cursor\n"
            "/tasks — لیست درخواست‌های اصلاح\n"
            "/clear — پاک کردن تاریخچه گفتگو\n"
            "/help — راهنما\n\n"
            "💬 هر پیام متنی = گفتگو با مشاور (نیاز به API Key)\n"
            "⚠️ اتصال تلگرام ≠ هوش مصنوعی — برای AI باید API Key تنظیم شود."
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.cmd_start(update, context)

    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        context.chat_data[CHAT_HISTORY_KEY] = []
        await update.message.reply_text("تاریخچه گفتگو پاک شد. از نو شروع کن 💬")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        session = get_session()
        try:
            analysis = self.analysis.analyze(session)
            await update.message.reply_text(
                overview_message(analysis),
                parse_mode="HTML",
            )
        finally:
            session.close()

    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        reload_runtime_settings()
        cfg = to_public_dict()
        llm_ok = is_llm_configured()
        lines = [
            "⚙️ <b>وضعیت مشاور AI</b>",
            "",
            f"مشاور: {'✅ فعال' if cfg['advisor_enabled'] else '❌ غیرفعال'}",
            f"LLM: {'✅ متصل' if llm_ok else '❌ API Key نیست'}",
            f"مدل: {cfg['advisor_model']}",
            f"تلگرام: {'✅' if cfg['telegram_configured'] else '❌'}",
            f"هشدار خودکار: {'✅' if cfg['advisor_telegram_proactive'] else '—'}",
        ]
        if not llm_ok:
            lines.extend([
                "",
                "⚠️ تلگرام وصل است ولی LLM نیست!",
                "",
                "یکی از این روش‌ها:",
                "۱) داشبورد → «۰ · ستاپ ایجنت» → API Key → ذخیره",
                "۲) تلگرام: /setkey sk-...",
            ])
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def cmd_setkey(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        args = context.args or []
        if not args:
            await update.message.reply_text(
                "استفاده:\n"
                "/setkey sk-...\n"
                "/setkey sk-... https://api.openai.com/v1 gpt-4o-mini\n\n"
                "یا از داشبورد → بخش ۰ · ستاپ ایجنت"
            )
            return
        api_key = args[0].strip()
        api_base = args[1].strip() if len(args) > 1 else None
        model = args[2].strip() if len(args) > 2 else None
        if not api_key.startswith("sk-") and len(api_key) < 20:
            await update.message.reply_text("فرمت API Key نامعتبر به نظر می‌رسد.")
            return
        try:
            set_api_key(api_key, api_base, model)
            await update.message.reply_text(
                "✅ API Key ذخیره شد.\n"
                f"مدل: {settings.advisor_model}\n"
                "الان یک پیام آزاد بفرست تا تست کنی."
            )
            try:
                await update.message.delete()
            except Exception:
                pass
        except Exception:
            logger.exception("setkey failed")
            await update.message.reply_text("خطا در ذخیره API Key")

    def _build_agent_context(self, session) -> dict:
        reload_runtime_settings()
        ctx = self.advisor.build_context(session)
        try:
            insight = self.advisor.generate_rules(ctx)
            ctx["advisor"] = {
                "headline": insight.headline,
                "problems": insight.problems,
                "ideas": insight.ideas,
                "conflicts": insight.conflicts,
            }
        except Exception:
            pass
        return ctx

    async def cmd_agent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        user_text = " ".join(context.args or []).strip()
        if not user_text:
            await update.message.reply_text(
                "استفاده:\n"
                "/agent توضیح مشکل یا درخواست اصلاح\n\n"
                "مثال:\n"
                "/agent بک‌تست ۴ ساعته ضعیف است، PF را بهبود بده"
            )
            return
        session = get_session()
        try:
            agent_ctx = self._build_agent_context(session)
            chat_id = str(update.effective_chat.id) if update.effective_chat else ""
            task = create_task(
                user_message=user_text,
                source="telegram",
                context=agent_ctx,
                chat_id=chat_id,
            )
            await update.message.reply_text(
                format_task_summary(task),
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("agent task failed")
            await update.message.reply_text("خطا در ثبت درخواست.")
        finally:
            session.close()

    async def cmd_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        tasks = list_tasks(5)
        if not tasks:
            await update.message.reply_text("درخواست اصلاحی ثبت نشده.")
            return
        lines = ["📋 <b>آخرین درخواست‌های اصلاح:</b>", ""]
        for t in tasks:
            status = t.get("status", "pending")
            lines.append(f"• <code>{t.get('id')}</code> — {status}")
            msg = (t.get("user_message") or "")[:60]
            if msg:
                lines.append(f"  {msg}...")
        lines.append("")
        lines.append("فایل‌ها در: data/agent_tasks/")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def cmd_advisor(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        if not settings.advisor_enabled:
            await update.message.reply_text("مشاور هوش مصنوعی غیرفعال است.")
            return

        session = get_session()
        try:
            insight = self.advisor.generate(session, force=True)
            await update.message.reply_text(
                advisor_message(insight),
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("Advisor command failed")
            await update.message.reply_text("خطا در تولید تحلیل مشاور. بعداً دوباره امتحان کن.")
        finally:
            session.close()

    async def _cmd_timeframe(self, update: Update, tf: str) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        session = get_session()
        try:
            analysis = self.analysis.analyze(session)
            await update.message.reply_text(
                timeframe_message(analysis.timeframes[tf]),
                parse_mode="HTML",
            )
        finally:
            session.close()

    async def cmd_4h(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        session = get_session()
        try:
            analysis = self.analysis.analyze(session)
            fc = self.forecast.build(session, analysis)
            await update.message.reply_text(
                forecast_4h_message(fc),
                parse_mode="HTML",
            )
        finally:
            session.close()

    async def cmd_1d(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._cmd_timeframe(update, "1d")

    async def cmd_1w(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._cmd_timeframe(update, "1w")

    async def handle_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return
        if not self._allowed(update):
            return await self._deny(update)

        reload_runtime_settings()

        if not settings.advisor_enabled or not settings.advisor_telegram_enabled:
            await update.message.reply_text(
                "گفتگوی آزاد غیرفعال است. از /status یا /advisor استفاده کن."
            )
            return

        user_text = update.message.text.strip()
        if user_text.startswith("/"):
            return

        agent_triggers = (
            "اصلاح کن", "درست کن", "fix", "cursor", "ایجنت", "agent",
            "کد را", "مشکل را حل", "به cursor", "به کرسر",
        )
        if any(t in user_text.lower() for t in agent_triggers):
            session = get_session()
            try:
                agent_ctx = self._build_agent_context(session)
                chat_id = str(update.effective_chat.id) if update.effective_chat else ""
                task = create_task(
                    user_message=user_text,
                    source="telegram",
                    context=agent_ctx,
                    chat_id=chat_id,
                )
                await update.message.reply_text(
                    format_task_summary(task),
                    parse_mode="HTML",
                )
            except Exception:
                logger.exception("agent task from chat failed")
                await update.message.reply_text("خطا در ثبت درخواست.")
            finally:
                session.close()
            return

        await update.message.chat.send_action("typing")

        session = get_session()
        try:
            if not settings.advisor_api_key:
                await update.message.reply_text(
                    "⚠️ API Key تنظیم نشده — الان فقط حالت ساده (rule-based) فعاله.\n\n"
                    "برای گفتگوی هوشمند:\n"
                    "• /setkey sk-...\n"
                    "• یا داشبورد → ۰ · ستاپ ایجنت\n\n"
                    "برای درخواست اصلاح کد:\n"
                    "• /agent توضیح مشکل"
                )
                history = list(self._get_history(context))
                reply = self.advisor.chat(session, user_text, history)
                self._append_history(context, "user", user_text)
                self._append_history(context, "assistant", reply)
                await update.message.reply_text(reply)
                return

            history = list(self._get_history(context))
            reply = self.advisor.chat(session, user_text, history)
            self._append_history(context, "user", user_text)
            self._append_history(context, "assistant", reply)
            await update.message.reply_text(reply)
        except Exception:
            logger.exception("Advisor chat failed")
            await update.message.reply_text("خطا در پاسخ‌دهی. دوباره امتحان کن یا /advisor بزن.")
        finally:
            session.close()

    def build_application(self) -> Application:
        if not settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

        app = Application.builder().token(settings.telegram_bot_token).build()
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("clear", self.cmd_clear))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("advisor", self.cmd_advisor))
        app.add_handler(CommandHandler("config", self.cmd_config))
        app.add_handler(CommandHandler("setkey", self.cmd_setkey))
        app.add_handler(CommandHandler("agent", self.cmd_agent))
        app.add_handler(CommandHandler("tasks", self.cmd_tasks))
        app.add_handler(CommandHandler("4h", self.cmd_4h))
        app.add_handler(CommandHandler("1d", self.cmd_1d))
        app.add_handler(CommandHandler("1w", self.cmd_1w))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_chat),
        )
        self._app = app
        return app

    def start_polling_background(self) -> None:
        import threading

        app = self.build_application()

        def _run() -> None:
            logger.info("Starting Telegram bot polling in background...")
            app.run_polling(drop_pending_updates=True, close_loop=False)

        thread = threading.Thread(target=_run, name="telegram-bot", daemon=True)
        thread.start()

    async def send_message(self, text: str) -> None:
        if not settings.telegram_chat_id:
            return
        bot = self._get_bot()
        for chat_id in settings.telegram_chat_id.split(","):
            await bot.send_message(
                chat_id=chat_id.strip(),
                text=text,
                parse_mode="HTML",
            )

    async def send_overview(self) -> None:
        session = get_session()
        try:
            analysis = self.analysis.analyze(session)
            await self.send_message(overview_message(analysis))
        finally:
            session.close()

    async def send_advisor_alert(self, insight) -> None:
        if not settings.advisor_telegram_proactive:
            return
        await self.send_message(advisor_alert_message(insight))


def run_telegram_bot() -> None:
    init_db()
    service = TelegramBotService()
    app = service.build_application()
    logger.info("Starting Telegram bot...")
    app.run_polling(drop_pending_updates=True)
