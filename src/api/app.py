from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc, select

from src.analyzer.serialize import analysis_to_dict
from src.analyzer.service import AnalysisService
from src.config import BASE_DIR, settings
from src.db.models import AnalysisSnapshot, OHLCVCandle, get_session, init_db

app = FastAPI(title="BTC Analyzer", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

analysis_service = AnalysisService()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


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


frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
