import logging

from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes, Update

from src.analyzer.service import AnalysisService
from src.config import settings
from src.db.models import get_session, init_db
from src.notifier.formatters import overview_message, timeframe_message

logger = logging.getLogger(__name__)

TF_COMMANDS = {
    "4h": "4h",
    "1d": "1d",
    "1w": "1w",
}


class TelegramBotService:
    def __init__(self) -> None:
        self.analysis = AnalysisService()
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

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        await update.message.reply_text(
            "سلام! من ربات تحلیل BTC هستم.\n\n"
            "دستورات:\n"
            "/status — خلاصه بازار\n"
            "/4h — تحلیل 4 ساعته\n"
            "/1d — تحلیل روزانه\n"
            "/1w — تحلیل هفتگی\n"
            "/help — راهنما"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.cmd_start(update, context)

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
        await self._cmd_timeframe(update, "4h")

    async def cmd_1d(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._cmd_timeframe(update, "1d")

    async def cmd_1w(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._cmd_timeframe(update, "1w")

    def build_application(self) -> Application:
        if not settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

        app = Application.builder().token(settings.telegram_bot_token).build()
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("4h", self.cmd_4h))
        app.add_handler(CommandHandler("1d", self.cmd_1d))
        app.add_handler(CommandHandler("1w", self.cmd_1w))
        self._app = app
        return app

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


def run_telegram_bot() -> None:
    init_db()
    service = TelegramBotService()
    app = service.build_application()
    logger.info("Starting Telegram bot...")
    app.run_polling(drop_pending_updates=True)
