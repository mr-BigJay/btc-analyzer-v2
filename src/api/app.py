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
        "architecture": "coinex→binance→deribit→technical→engine→outlook/plan→bitunix",
        "phase": "rewrite-foundation",
        "docs": "01-vision-architecture",
    }


@app.get("/api/v1/architecture")
def architecture():
    return {
        "pipeline": [
            "coinex_narrative",
            "binance_futures",
            "deribit_options",
            "technical_structure",
            "ai_decision_engine",
            "daily_outlook",
            "intraday_trading_plan",
            "bitunix_execution_validation",
        ],
        "philosophy": "multi-evidence-only",
        "daily_outlook_utc": f"{settings.daily_outlook_hour_utc:02d}:{settings.daily_outlook_minute_utc:02d}",
    }


frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
