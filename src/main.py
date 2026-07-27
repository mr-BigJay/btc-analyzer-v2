"""CLI entrypoint for BTC Analyzer v3 rewrite."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import uvicorn

from src import __version__
from src.config import settings
from src.db.models import init_db
from src.logging_setup import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def cmd_init_db() -> int:
    init_db()
    logger.info("Database initialized at %s", settings.database_url)
    return 0


def cmd_status() -> int:
    print(f"BTC Analyzer {__version__}")
    print("Product: Decision Support System (DSS)")
    print("Phase: Enterprise Design Book — Chapter 5 (Backend Architecture)")
    print("Stack: FastAPI · Uvicorn · PostgreSQL · Redis · APScheduler · Loguru · Nginx")
    print("Services: Collection · Analysis · Market · WebSocket · Scheduler")
    print("API: /api/v1 · envelope {status,timestamp,request_id,data} · /ws")
    print(f"Database: {settings.database_url}")
    print(f"Redis: {settings.redis_url or 'memory-fallback'}")
    print(f"Timezone: {settings.timezone} · Log: {settings.log_level}")
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


def cmd_collect() -> int:
    from src.services import CollectionService

    init_db()
    result = CollectionService().run_full()
    print(f"ok={result.ok} warnings={result.warnings}")
    if result.snapshot:
        print(f"symbol={result.snapshot.symbol} price={result.snapshot.price}")
    return 0 if result.ok else 1


def cmd_migrate() -> int:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    command.upgrade(cfg, "head")
    logger.info("Alembic upgrade head complete")
    return 0


def cmd_retention() -> int:
    from src.db.retention import apply_retention

    init_db()
    deleted = apply_retention()
    print(f"retention deleted={deleted}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=f"BTC Analyzer {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="Show rewrite status")
    sub.add_parser("init-db", help="Initialize database schema + seed reference data")
    sub.add_parser("serve", help="Start API + WebSocket + dashboard")
    sub.add_parser("run", help="Start scheduler (Ch.5 intervals)")
    sub.add_parser("collect", help="Run one full data collection cycle")
    sub.add_parser("migrate", help="Run Alembic migrations (upgrade head)")
    sub.add_parser("retention", help="Apply Ch.4 retention policy")

    args = parser.parse_args()
    commands = {
        "status": cmd_status,
        "init-db": cmd_init_db,
        "serve": cmd_serve,
        "run": cmd_run,
        "collect": cmd_collect,
        "migrate": cmd_migrate,
        "retention": cmd_retention,
    }
    if args.command in commands:
        return commands[args.command]()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
