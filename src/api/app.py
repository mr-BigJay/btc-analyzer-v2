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
        "phase": "rewrite-ch03",
        "chapter": "03-data-collection-engine",
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
        "data_collection": {
            "providers": {
                "binance": "futures_market_reference",
                "deribit": "options_market_intelligence",
                "coinex": "daily_narrative",
                "bitunix": "execution_validation",
            },
            "pipeline": [
                "collectors",
                "validators",
                "normalizers",
                "cache",
                "database",
            ],
            "scheduler": {
                "realtime": "trades_orderbook_liquidations",
                "1m": "price_funding_open_interest",
                "5m": "technical_cache",
                "1h": "option_chain",
                "daily_utc": f"{settings.daily_outlook_hour_utc:02d}:{settings.daily_outlook_minute_utc:02d}",
            },
            "retry_sec": [5, 15, 30],
        },
        "analysis_engines": [
            "futures",
            "options",
            "technical",
            "pattern",
            "structure",
        ],
        "design_rules": {
            "decision_engine_only_recommendations": True,
            "binance_futures_reference": True,
            "bitunix_execution_validation_only": True,
            "collectors_isolated": True,
            "append_only_history": True,
            "utc_timestamps": True,
            "fault_tolerance_required": True,
            "secrets_via_env_only": True,
        },
        "daily_outlook_utc": f"{settings.daily_outlook_hour_utc:02d}:{settings.daily_outlook_minute_utc:02d}",
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
    """Trigger one full collection cycle (manual)."""
    from src.collectors.engine import DataCollectionEngine

    engine = DataCollectionEngine()
    result = engine.run_full_cycle_sync()
    return result.to_dict()


frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
