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
                "event_bus",
                "storage",
                "analysis",
                "ai",
                "presentation",
            ],
            "collection_integration": {
                "chapter": 12,
                "interface": ["connect", "collect", "validate", "normalize", "publish"],
                "collector_types": ["spot", "futures", "options", "volatility", "macro"],
                "providers": ["binance", "deribit", "coinex", "bitunix"],
                "health_states": ["Healthy", "Degraded", "Recovering", "Offline"],
                "endpoints": [
                    "/api/v1/collection/status",
                    "/api/v1/collection/health",
                    "/api/v1/collection/events",
                    "/api/v1/collection/quarantine",
                    "/api/v1/collection/backfill",
                ],
            },
            "feature_engineering": {
                "chapter": 13,
                "categories": [
                    "price",
                    "volume",
                    "derivatives",
                    "options",
                    "technical",
                    "structural",
                    "liquidity",
                    "volatility",
                    "composite",
                ],
                "normalization": {"directional": [-100, 100], "probability": [0, 100], "ratio": [0, 1]},
                "endpoints": [
                    "/api/v1/features/status",
                    "/api/v1/features/latest",
                    "/api/v1/features/engineer",
                    "/api/v1/features/quarantine",
                ],
            },
            "validation": {
                "chapter": 14,
                "methods": [
                    "historical_backtest",
                    "walk_forward",
                    "paper_trading",
                    "shadow_mode",
                    "continuous_validation",
                ],
                "horizons": ["1h", "4h", "24h", "7d"],
                "endpoints": [
                    "/api/v1/validation/status",
                    "/api/v1/validation/dashboard",
                    "/api/v1/validation/backtest",
                    "/api/v1/validation/walk-forward",
                    "/api/v1/validation/evaluate",
                    "/api/v1/validation/approve",
                ],
            },
            "risk_management": {
                "chapter": 15,
                "composite_risk_score": "0-100",
                "categories": [
                    "market",
                    "liquidity",
                    "volatility",
                    "leverage",
                    "event",
                    "data",
                    "execution",
                ],
                "controls": [
                    "exposure_sizing",
                    "no_trade_zone",
                    "volatility_adjustment",
                    "confidence_risk_matrix",
                ],
                "governance": [
                    "deterministic",
                    "ai_cannot_override",
                    "suppression_logged",
                ],
                "endpoints": [
                    "/api/v1/risk/status",
                    "/api/v1/risk/latest",
                    "/api/v1/risk/evaluate",
                    "/api/v1/risk/apply-plan",
                ],
            },
            "alerting_events": {
                "chapter": 16,
                "lifecycle": [
                    "detection",
                    "validation",
                    "classification",
                    "correlation",
                    "deduplication",
                    "priority",
                    "notification",
                    "archive",
                ],
                "channels": ["API", "Dashboard", "Telegram", "WebSocket"],
                "endpoints": [
                    "/api/v1/events/status",
                    "/api/v1/events/list",
                    "/api/v1/events/dashboard",
                    "/api/v1/events/process",
                    "/api/v1/events/system",
                    "/api/v1/events/analytics",
                ],
            },
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
                "chapter": 11,
                "domains": [
                    "market_data",
                    "technical_analysis",
                    "options_analytics",
                    "ai_analysis",
                    "system",
                    "configuration",
                    "scores",
                    "ai_decisions",
                    "reports",
                    "alerts",
                ],
                "data_package": "/api/v1/db/package",
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
            "report_generation": {
                "types": [
                    "Daily Outlook",
                    "Intraday Trading Plan",
                    "Market Snapshot",
                    "Futures Report",
                    "Options Report",
                    "Liquidity Report",
                    "Risk Report",
                    "Weekly Summary",
                    "Alert Notification",
                ],
                "audiences": ["executive", "professional", "analyst"],
                "channels": ["api", "dashboard", "telegram", "websocket", "export"],
                "endpoints": ["/api/v1/market/outlook", "/api/v1/market/report"],
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
            {
                "id": e.id,
                "name": e.name,
                "priority": e.priority,
                "status": e.status,
                "api_status": getattr(e, "api_status", None),
                "last_sync": e.last_sync.isoformat() if getattr(e, "last_sync", None) else None,
            }
            for e in session.query(Exchange).all()
        ]
        symbols = [
            {
                "id": s.id,
                "public_id": getattr(s, "public_id", None),
                "symbol": s.symbol,
                "base_asset": s.base_asset,
                "quote_asset": s.quote_asset,
                "status": s.status,
            }
            for s in session.query(Symbol).all()
        ]
    finally:
        session.close()
    return success(
        {
            "database_url_dialect": "postgresql" if settings.is_postgres else "sqlite",
            "exchanges": exchanges,
            "symbols": symbols,
            "cache": redis_cache.snapshot(),
            "data_model_chapter": 11,
            "retention": {
                "trades_days": 90,
                "orderbook_days": 30,
                "tick_candles_days": 14,
                "analysis_permanent": True,
                "reports_permanent": True,
            },
        },
        request_id=request_id,
    )


@router.get("/db/package")
def db_package(request: Request, symbol: str = "BTCUSDT"):
    """Standardized data package (Ch.11 §11.26)."""
    from src.db.packages import build_data_package

    request_id = getattr(request.state, "request_id", None)
    return success(build_data_package(symbol=symbol), request_id=request_id)
