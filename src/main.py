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
    print("Phase: Enterprise Design Book — Chapter 9 (Scoring & Decision Model)")
    print("Pipeline: Analysis → Intelligence → Scoring (MBS/CS/RS/DQS) → AI Decision")
    print("Stack: FastAPI · PostgreSQL · Redis · APScheduler · Loguru")
    print(f"Database: {settings.database_url}")
    print(f"Redis: {settings.redis_url or 'memory-fallback'}")
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


def cmd_analyze() -> int:
    from src.services import AnalysisService

    init_db()
    out = AnalysisService().run_full()
    print(f"bias={out['market_bias']} conf={out['confidence']} regime={out['market_regime']}")
    print(f"primary={out['primary_scenario']} risk={out['risk_level']}")
    print(f"scenarios={[s['name']+':'+str(s['probability']) for s in out.get('scenarios', [])]}")
    return 0


def cmd_outlook() -> int:
    from src.services import DecisionService

    init_db()
    out = DecisionService().run(multi_timeframe=False)
    intel = out.get("market_intelligence") or {}
    print(f"bias={out['market_bias']} conf={out['confidence']} band={out['confidence_band']}")
    print(f"narrative={out['primary_narrative']} risk={out['risk_level']}")
    print(
        f"regime={out['market_regime']} cycle={intel.get('market_cycle')} "
        f"mhi={intel.get('market_health_index')} msi={intel.get('market_stress_index')}"
    )
    print(f"primary={out['primary_scenario']}")
    print(f"scenarios={[s['name']+':'+str(s['probability']) for s in out.get('scenarios', [])]}")
    print(f"plan={out['trading_plan'].get('preferred_direction')}")
    summary = (out.get("daily_outlook") or {}).get("executive_summary") or ""
    print(f"summary={summary[:240]}")
    return 0


def cmd_intelligence() -> int:
    from src.services import IntelligenceService

    init_db()
    out = IntelligenceService().run(multi_timeframe=False)
    print(f"regime={out['market_regime']} cycle={out['market_cycle']}")
    print(f"participant={out['dominant_participant']} institutional={out['institutional_activity']}")
    print(f"mhi={out['market_health_index']} ({out['market_health_band']}) msi={out['market_stress_index']}")
    print(f"vol={out['volatility_regime']} liquidity={out['liquidity_state']}")
    print(f"macro={out['macro_bias']} cross_asset={out['cross_asset_bias']}")
    print(f"transition={out['transition_probability']}% {out.get('detected_transitions')}")
    print(f"derivatives={out.get('derivatives_thesis')}")
    return 0


def cmd_score() -> int:
    from src.services import ScoringService

    init_db()
    out = ScoringService().run(multi_timeframe=False)
    print(f"bias={out['market_bias']} mbs={out['market_bias_score']} decision={out['decision']}")
    print(f"cs={out['confidence_score']} rs={out['risk_score']} dqs={out['data_quality_score']}")
    print(f"mhi={out['market_health_index']} msi={out['market_stress_index']}")
    print(f"alignment={out['timeframe_alignment']} weights={out['weight_regime']} publish={out['publish']}")
    print(f"layer_scores={out.get('layer_scores')}")
    return 0


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
    sub.add_parser("analyze", help="Run Chapter 6 Analysis Engine once")
    sub.add_parser("intelligence", help="Run Chapter 8 Market Intelligence Framework")
    sub.add_parser("score", help="Run Chapter 9 Scoring & Decision Model")
    sub.add_parser("outlook", help="Run Chapter 7 AI Decision Engine / Daily Outlook")
    sub.add_parser("migrate", help="Run Alembic migrations (upgrade head)")
    sub.add_parser("retention", help="Apply Ch.4 retention policy")

    args = parser.parse_args()
    commands = {
        "status": cmd_status,
        "init-db": cmd_init_db,
        "serve": cmd_serve,
        "run": cmd_run,
        "collect": cmd_collect,
        "analyze": cmd_analyze,
        "intelligence": cmd_intelligence,
        "score": cmd_score,
        "outlook": cmd_outlook,
        "migrate": cmd_migrate,
        "retention": cmd_retention,
    }
    if args.command in commands:
        return commands[args.command]()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
