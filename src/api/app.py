from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc, select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.options_routes import router as options_router
from src.advisor.routes import router as advisor_router
from src.analyzer.forecast import ForecastEngine, forecast_to_dict
from src.analyzer.serialize import analysis_to_dict
from src.analyzer.service import AnalysisService
from src.config import BASE_DIR, settings
from src.db.models import (
    AnalysisSnapshot,
    BacktestResult,
    LiquidationLevel,
    OptimizedParams,
    OHLCVCandle,
    get_session,
    init_db,
)

app = FastAPI(title="BTC Analyzer", version="2.4.0")
FRONTEND_BUILD = "2024.06-advisor-setup-v3"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoCacheHtmlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.endswith(".html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


app.add_middleware(NoCacheHtmlMiddleware)

analysis_service = AnalysisService()
forecast_engine = ForecastEngine()

app.include_router(advisor_router)
app.include_router(options_router)


@app.on_event("startup")
def startup() -> None:
    from src.advisor.settings_store import apply_from_disk

    init_db()
    apply_from_disk()


@app.get("/api/health")
def health():
    return {"status": "ok", "frontend_build": FRONTEND_BUILD, "version": "2.4.0"}


@app.get("/api/v1/overview")
def overview():
    session = get_session()
    try:
        analysis = analysis_service.analyze(session)
        return analysis_to_dict(analysis)
    finally:
        session.close()


@app.get("/api/v1/timeframe/{tf}")
def timeframe(tf: str):
    if tf not in settings.timeframes:
        raise HTTPException(404, f"Invalid timeframe: {tf}")
    session = get_session()
    try:
        analysis = analysis_service.analyze(session)
        return analysis_to_dict(analysis.timeframes[tf])
    finally:
        session.close()


@app.get("/api/v1/chart/{tf}")
def chart(tf: str, limit: int = 100):
    if tf not in settings.timeframes:
        raise HTTPException(404, f"Invalid timeframe: {tf}")
    session = get_session()
    try:
        stmt = (
            select(OHLCVCandle)
            .where(OHLCVCandle.symbol == settings.symbol, OHLCVCandle.timeframe == tf)
            .order_by(desc(OHLCVCandle.open_time))
            .limit(limit)
        )
        rows = list(reversed(session.execute(stmt).scalars().all()))
        return {
            "timeframe": tf,
            "candles": [
                {
                    "time": r.open_time.isoformat(),
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                }
                for r in rows
            ],
        }
    finally:
        session.close()


@app.get("/api/v1/signals")
def signals(limit: int = 20):
    session = get_session()
    try:
        rows = session.execute(
            select(AnalysisSnapshot).order_by(desc(AnalysisSnapshot.created_at)).limit(limit)
        ).scalars().all()
        return [
            {
                "id": r.id,
                "overall_score": r.overall_score,
                "overall_confidence": r.overall_confidence,
                "summary": r.summary,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        session.close()


@app.get("/api/v1/backtest")
def backtest_results(limit: int = 10):
    session = get_session()
    try:
        rows = session.execute(
            select(BacktestResult).order_by(desc(BacktestResult.created_at)).limit(limit)
        ).scalars().all()
        return [
            {
                "timeframe": r.timeframe,
                "total_signals": r.total_signals,
                "win_rate": r.win_rate,
                "profit_factor": r.profit_factor,
                "avg_return_pct": r.avg_return_pct,
                "max_drawdown_pct": r.max_drawdown_pct,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        session.close()


@app.get("/api/v1/liquidations")
def liquidation_map():
    session = get_session()
    try:
        rows = session.execute(
            select(LiquidationLevel)
            .order_by(desc(LiquidationLevel.snapshot_at))
            .limit(30)
        ).scalars().all()
        if not rows:
            return {"zones": [], "total_usd": 0}
        latest = rows[0].snapshot_at
        zones = [
            {
                "price": r.price_level,
                "long_usd": r.long_liq_usd,
                "short_usd": r.short_liq_usd,
                "total_usd": r.total_usd,
            }
            for r in rows
            if r.snapshot_at == latest
        ]
        zones.sort(key=lambda z: z["price"])
        return {
            "zones": zones,
            "total_usd": sum(z["total_usd"] for z in zones),
            "updated_at": latest.isoformat(),
        }
    finally:
        session.close()


@app.get("/api/v1/forecast/4h")
def forecast_4h():
    session = get_session()
    try:
        analysis = analysis_service.analyze(session)
        forecast = forecast_engine.build(session, analysis)
        return forecast_to_dict(forecast)
    finally:
        session.close()


@app.get("/api/v1/optimized-params")
def optimized_params():
    session = get_session()
    try:
        from src.analyzer.optimize import BacktestOptimizer

        params = BacktestOptimizer.get_all_best(session)
        return {
            tf: {
                "confidence": p.confidence_threshold,
                "min_score_bull": p.min_score_bull,
                "max_score_bear": p.max_score_bear,
                "win_rate": p.win_rate,
                "profit_factor": p.profit_factor,
                "updated_at": p.created_at.isoformat(),
            }
            for tf, p in params.items()
        }
    finally:
        session.close()


frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
