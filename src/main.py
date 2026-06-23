import argparse
import logging
import sys

from datetime import datetime, timezone

import uvicorn

from src.analyzer.backtest import BacktestEngine
from src.analyzer.serialize import analysis_to_json
from src.analyzer.service import AnalysisService
from src.collector.orchestrator import CollectionOrchestrator
from src.config import settings
from src.db.models import AnalysisSnapshot, get_session, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def cmd_collect() -> int:
    init_db()
    orchestrator = CollectionOrchestrator()
    results = orchestrator.run_all()
    errors = [k for k, v in results.items() if v.get("status") == "error"]
    if errors:
        logger.error("Collection finished with errors: %s", errors)
        return 1
    total = sum(v.get("records", 0) for v in results.values())
    logger.info("Collection complete — %d total records", total)
    return 0


def cmd_analyze() -> int:
    init_db()
    session = get_session()
    try:
        service = AnalysisService()
        analysis = service.analyze(session)
        snapshot = AnalysisSnapshot(
            payload=analysis_to_json(analysis),
            overall_score=analysis.overall_score,
            overall_confidence=analysis.overall_confidence,
            summary=analysis.summary,
            created_at=datetime.now(timezone.utc),
        )
        session.add(snapshot)
        session.commit()
        logger.info("Analysis: score=%.1f confidence=%.1f", analysis.overall_score, analysis.overall_confidence)
        logger.info("Summary: %s", analysis.summary)
        for tf in settings.timeframes:
            t = analysis.timeframes[tf]
            logger.info("  %s: %s score=%.1f confidence=%.1f", tf, t.trend.value, t.score, t.confidence)
        return 0
    finally:
        session.close()


def cmd_backtest() -> int:
    init_db()
    session = get_session()
    try:
        engine = BacktestEngine()
        reports = engine.run_all_timeframes(session)
        for r in reports:
            print(
                f"\n=== {r.timeframe} ===\n"
                f"Signals: {r.total_signals} | Win rate: {r.win_rate}% | "
                f"PF: {r.profit_factor} | Avg return: {r.avg_return_pct}% | "
                f"Max DD: {r.max_drawdown_pct}%"
            )
        return 0
    finally:
        session.close()


def cmd_init_db() -> int:
    init_db()
    logger.info("Database initialized at %s", settings.database_url)
    return 0


def cmd_serve() -> int:
    init_db()
    uvicorn.run("src.api.app:app", host=settings.api_host, port=settings.api_port, reload=False)
    return 0


def cmd_run() -> int:
    from src.scheduler import AppScheduler

    try:
        from src.notifier.telegram_bot import TelegramBotService

        telegram = TelegramBotService() if settings.telegram_bot_token else None
        if telegram:
            telegram.build_application()
    except Exception:
        logger.warning("Telegram bot not configured")
        telegram = None

    scheduler = AppScheduler(telegram_service=telegram)
    scheduler.start()
    return 0


def cmd_telegram() -> int:
    from src.notifier.telegram_bot import run_telegram_bot

    run_telegram_bot()
    return 0


def cmd_start() -> int:
    """Run scheduler (background) + API server (foreground)."""
    import threading

    from src.scheduler import AppScheduler

    init_db()

    telegram = None
    if settings.telegram_bot_token:
        try:
            from src.notifier.telegram_bot import TelegramBotService

            telegram = TelegramBotService()
            telegram.build_application()
        except Exception:
            logger.warning("Telegram alerts disabled")

    scheduler = AppScheduler(telegram_service=telegram)
    thread = threading.Thread(target=scheduler.start, daemon=True)
    thread.start()
    logger.info("Scheduler running in background")
    uvicorn.run("src.api.app:app", host=settings.api_host, port=settings.api_port, reload=False)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="BTC Analyzer")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("collect", help="Collect all market data")
    sub.add_parser("analyze", help="Run analysis on collected data")
    sub.add_parser("init-db", help="Initialize database")
    sub.add_parser("serve", help="Start API + dashboard")
    sub.add_parser("run", help="Start scheduler (collect + analyze loop)")
    sub.add_parser("start", help="Scheduler + dashboard API together")
    sub.add_parser("backtest", help="Run walk-forward backtest")
    sub.add_parser("telegram", help="Start Telegram bot")

    args = parser.parse_args()
    commands = {
        "collect": cmd_collect,
        "analyze": cmd_analyze,
        "backtest": cmd_backtest,
        "init-db": cmd_init_db,
        "serve": cmd_serve,
        "run": cmd_run,
        "start": cmd_start,
        "telegram": cmd_telegram,
    }
    if args.command in commands:
        return commands[args.command]()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
