"""System / architecture / DB status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.responses import success
from src.config import settings

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/architecture")
def architecture(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(
        {
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
            "backend": {
                "framework": "fastapi",
                "asgi": "uvicorn",
                "scheduler": "apscheduler",
                "logging": "loguru",
                "websocket": True,
                "reverse_proxy": "nginx",
            },
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
            },
            "analysis_engine": {
                "layers": [
                    "Spot",
                    "Futures",
                    "Options",
                    "Technical",
                    "Market Structure",
                    "Pattern Detection",
                    "Volatility",
                    "Liquidity",
                ],
                "pipeline": [
                    "layer_analysis",
                    "scoring",
                    "conflict_resolution",
                    "scenarios",
                ],
                "endpoint": "/api/v1/market/analysis",
                "ai_inference_in_layers": False,
            },
            "market_intelligence": {
                "consumes": "MarketAnalysisOutput",
                "feeds": "AIDecisionEngine",
                "outputs": [
                    "market_regime",
                    "market_cycle",
                    "MHI",
                    "MSI",
                    "participants",
                    "liquidity_state",
                    "transitions",
                ],
                "endpoint": "/api/v1/market/intelligence",
            },
            "scoring_decision_model": {
                "layer_score_range": [-100, 100],
                "composites": ["MBS", "CS", "RS", "MHI", "MSI", "DQS"],
                "decision_matrix_weights": {
                    "MBS": 0.40,
                    "CS": 0.25,
                    "RS": 0.15,
                    "MHI": 0.10,
                    "MSI": 0.10,
                },
                "endpoint": "/api/v1/market/scoring",
            },
            "ai_decision_engine": {
                "consumes": "MarketAnalysisOutput",
                "raw_exchange_access": False,
                "pipeline": [
                    "evidence_aggregation",
                    "signal_prioritization",
                    "narrative_detection",
                    "probability_estimation",
                    "risk_assessment",
                    "nlg",
                ],
                "endpoints": [
                    "/api/v1/market/decision",
                    "/api/v1/market/outlook",
                    "/api/v1/market/trading-plan",
                ],
            },
            "scheduler": {
                "realtime": "websocket_streams",
                "1m": "funding_oi_trades",
                "5m": "technical_indicators",
                "15m": "pattern_detection",
                "1h": "options_metrics",
                "daily_utc": f"{settings.daily_outlook_hour_utc:02d}:{settings.daily_outlook_minute_utc:02d}",
            },
            "design_rules": {
                "service_interfaces_only": True,
                "no_cross_module_db_access": True,
                "api_versioned": True,
                "utc_timestamps": True,
                "secrets_via_env_only": True,
            },
        },
        request_id=request_id,
    )


@router.get("/db/status")
def db_status(request: Request):
    from src.db.models import Exchange, Symbol
    from src.db.session import get_session
    from src.storage.redis_cache import redis_cache

    request_id = getattr(request.state, "request_id", None)
    session = get_session()
    try:
        exchanges = [
            {"id": e.id, "name": e.name, "priority": e.priority, "status": e.status}
            for e in session.query(Exchange).all()
        ]
        symbols = [{"id": s.id, "symbol": s.symbol, "status": s.status} for s in session.query(Symbol).all()]
    finally:
        session.close()
    return success(
        {
            "database_url_dialect": "postgresql" if settings.is_postgres else "sqlite",
            "exchanges": exchanges,
            "symbols": symbols,
            "cache": redis_cache.snapshot(),
        },
        request_id=request_id,
    )
