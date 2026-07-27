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
        "phase": "rewrite-ch01",
        "chapter": "01-introduction",
    }


@app.get("/api/v1/architecture")
def architecture():
    return {
        "workflow": [
            "data_collection",
            "data_validation",
            "data_normalization",
            "analysis_engine",
            "probability_engine",
            "daily_outlook",
            "intraday_trading_plan",
            "trade_execution_validation",
        ],
        "principles": [
            "evidence_based_analysis",
            "probability_over_prediction",
            "modular_architecture",
            "transparency",
            "risk_first",
        ],
        "scope_v1": [
            "bitcoin",
            "binance_futures",
            "deribit_options",
            "coinex_daily_analysis",
            "bitunix_execution_validation",
            "technical_analysis",
            "ai_decision_engine",
            "daily_outlook",
            "intraday_trading_plan",
        ],
        "daily_outlook_utc": f"{settings.daily_outlook_hour_utc:02d}:{settings.daily_outlook_minute_utc:02d}",
    }


frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
