"""FastAPI application — decision-support API surface."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src import __version__
from src.config import BASE_DIR, settings
from src.db.models import init_db

app = FastAPI(
    title="BTC Analyzer",
    version=__version__,
    description="Market intelligence & decision support — rewrite v3",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": __version__,
        "product": "decision-support-system",
        "phase": "rewrite-ch04",
        "chapter": "04-database-design",
        "database": "postgresql" if settings.is_postgres else "sqlite",
        "redis_configured": bool(settings.redis_url),
    }


@app.get("/api/v1/architecture")
def architecture():
    return {
        "layers": [
            "data_sources",
            "collection",
            "validation",
            "normalization",
            "storage",
            "analysis",
            "ai",
            "presentation",
        ],
        "database": {
            "ssot": True,
            "primary": "postgresql",
            "cache": "redis",
            "orm": "sqlalchemy",
            "migrations": "alembic",
            "domains": [
                "market_data",
                "technical_analysis",
                "options_analytics",
                "ai_analysis",
                "system",
                "configuration",
            ],
            "retention": {"trades_days": 90, "orderbook_days": 30},
        },
        "data_collection": {
            "providers": {
                "binance": "futures_market_reference",
                "deribit": "options_market_intelligence",
                "coinex": "ai_research_narrative",
                "bitunix": "execution_validation",
            },
            "scheduler": {
                "realtime": "trades_orderbook_liquidations",
                "1m": "price_funding_open_interest",
                "5m": "technical_cache",
                "1h": "option_chain",
                "daily_utc": f"{settings.daily_outlook_hour_utc:02d}:{settings.daily_outlook_minute_utc:02d}",
            },
        },
        "design_rules": {
            "decision_engine_only_recommendations": True,
            "binance_futures_reference": True,
            "bitunix_execution_validation_only": True,
            "collectors_isolated": True,
            "append_only_history": True,
            "fk_integrity_required": True,
            "utc_timestamps": True,
            "secrets_via_env_only": True,
        },
        "daily_outlook_utc": f"{settings.daily_outlook_hour_utc:02d}:{settings.daily_outlook_minute_utc:02d}",
    }


@app.get("/api/v1/db/status")
def db_status():
    from src.db.models import Exchange, Symbol
    from src.db.session import get_session
    from src.storage.redis_cache import redis_cache

    session = get_session()
    try:
        exchanges = [{"id": e.id, "name": e.name, "priority": e.priority, "status": e.status} for e in session.query(Exchange).all()]
        symbols = [{"id": s.id, "symbol": s.symbol, "status": s.status} for s in session.query(Symbol).all()]
    finally:
        session.close()
    return {
        "database_url_dialect": "postgresql" if settings.is_postgres else "sqlite",
        "exchanges": exchanges,
        "symbols": symbols,
        "cache": redis_cache.snapshot(),
    }


@app.get("/api/v1/collection/status")
def collection_status():
    from src.storage.cache import global_cache
    from src.storage.repository import CentralRepository

    repo = CentralRepository()
    return {
        "enabled": {
            "binance": settings.binance_futures_enabled,
            "deribit": settings.deribit_enabled,
            "coinex": settings.coinex_enabled,
            "bitunix": settings.bitunix_enabled,
        },
        "hot_cache_keys": list(global_cache.snapshot().keys()),
        "snapshots_present": {
            "Binance": repo.load_snapshot("Binance") is not None,
            "Deribit": repo.load_snapshot("Deribit") is not None,
            "CoinEx": repo.load_snapshot("CoinEx") is not None,
            "Bitunix": repo.load_snapshot("Bitunix") is not None,
        },
    }


@app.post("/api/v1/collection/run")
def collection_run():
    from src.collectors.engine import DataCollectionEngine

    engine = DataCollectionEngine()
    result = engine.run_full_cycle_sync()
    return result.to_dict()


frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
