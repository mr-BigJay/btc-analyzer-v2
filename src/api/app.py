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
        "phase": "rewrite-ch02",
        "chapter": "02-system-architecture",
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
        "analysis_engines": [
            "futures",
            "options",
            "technical",
            "pattern",
            "structure",
        ],
        "object_flow": [
            "narrative_object",
            "flow_object",
            "options_object",
            "chart_object",
            "probability_object",
            "daily_outlook",
            "intraday_setup",
        ],
        "design_rules": {
            "decision_engine_only_recommendations": True,
            "binance_futures_reference": True,
            "bitunix_execution_validation_only": True,
            "utc_timestamps": True,
            "fault_tolerance_required": True,
        },
        "daily_outlook_utc": f"{settings.daily_outlook_hour_utc:02d}:{settings.daily_outlook_minute_utc:02d}",
    }


frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
