"""CLI entrypoint for BTC Analyzer v3 rewrite."""

from __future__ import annotations

import argparse
import logging
import sys

import uvicorn

from src import __version__
from src.config import settings
from src.db.models import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def cmd_init_db() -> int:
    init_db()
    logger.info("Database initialized at %s", settings.database_url)
    return 0


def cmd_status() -> int:
    print(f"BTC Analyzer {__version__}")
    print("Phase: rewrite foundation (Design Doc 01)")
    print("Pipeline: CoinEx → Binance → Deribit → Technical → Engine → Outlook/Plan → Bitunix")
    print(f"Daily Outlook UTC: {settings.daily_outlook_hour_utc:02d}:{settings.daily_outlook_minute_utc:02d}")
    return 0


def cmd_serve() -> int:
    init_db()
    uvicorn.run("src.api.app:app", host=settings.api_host, port=settings.api_port, reload=False)
    return 0


def cmd_run() -> int:
    from src.scheduler import AppScheduler

    init_db()
    AppScheduler().start()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=f"BTC Analyzer {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="Show rewrite status")
    sub.add_parser("init-db", help="Initialize database")
    sub.add_parser("serve", help="Start API + dashboard")
    sub.add_parser("run", help="Start scheduler (stubs until Doc 02+)")

    args = parser.parse_args()
    commands = {
        "status": cmd_status,
        "init-db": cmd_init_db,
        "serve": cmd_serve,
        "run": cmd_run,
    }
    if args.command in commands:
        return commands[args.command]()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
