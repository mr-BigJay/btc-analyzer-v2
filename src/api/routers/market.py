"""Market / dashboard read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.responses import success
from src.services import AnalysisService, DecisionService, IntelligenceService, MarketService, ScoringService

router = APIRouter(prefix="/api/v1/market", tags=["market"])


@router.get("/snapshot")
def market_snapshot(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(MarketService().snapshot(), request_id=request_id)


@router.get("/analysis")
def full_analysis(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(AnalysisService().run_full(), request_id=request_id)


@router.get("/intelligence")
def market_intelligence(request: Request):
    """Market Intelligence Framework (Ch.8)."""
    request_id = getattr(request.state, "request_id", None)
    return success(IntelligenceService().run(multi_timeframe=False), request_id=request_id)


@router.get("/scoring")
def scoring_decision(request: Request):
    """Scoring & Decision Model object (Ch.9 §9.16)."""
    request_id = getattr(request.state, "request_id", None)
    return success(ScoringService().run(multi_timeframe=False), request_id=request_id)


@router.get("/decision")
def ai_decision(request: Request):
    """AI Decision Engine report (Ch.7) with Ch.8 context."""
    request_id = getattr(request.state, "request_id", None)
    return success(DecisionService().run(multi_timeframe=False), request_id=request_id)


@router.get("/outlook")
def daily_outlook(request: Request):
    """Daily Outlook flagship report (Ch.7 §7.13)."""
    request_id = getattr(request.state, "request_id", None)
    return success(DecisionService().outlook(multi_timeframe=False), request_id=request_id)


@router.get("/trading-plan")
def trading_plan(request: Request):
    """Intraday Trading Plan (Ch.7 §7.14)."""
    request_id = getattr(request.state, "request_id", None)
    return success(DecisionService().trading_plan(multi_timeframe=False), request_id=request_id)


@router.get("/patterns")
def patterns(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(AnalysisService().detect_patterns(), request_id=request_id)


@router.get("/technical")
def technical(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(AnalysisService().refresh_technical(), request_id=request_id)
