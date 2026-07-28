"""Market / dashboard read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from src.api.responses import success
from src.services import (
    AnalysisService,
    DecisionService,
    IntelligenceService,
    MarketService,
    ReportService,
    ScoringService,
)

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
    """AI Decision Engine report (Ch.7) with Ch.8/9 context."""
    request_id = getattr(request.state, "request_id", None)
    return success(DecisionService().run(multi_timeframe=False), request_id=request_id)


@router.get("/outlook")
def daily_outlook(
    request: Request,
    audience: str = Query("professional"),
    language: str = Query("en"),
):
    """Daily Outlook presentation report (Ch.10)."""
    request_id = getattr(request.state, "request_id", None)
    return success(
        ReportService().daily_outlook(audience=audience, language=language, persist=True),
        request_id=request_id,
    )


@router.get("/report")
def generate_report(
    request: Request,
    type: str = Query("Daily Outlook", alias="type"),
    audience: str = Query("professional"),
    language: str = Query("en"),
):
    """Canonical report generation (Ch.10)."""
    request_id = getattr(request.state, "request_id", None)
    return success(
        ReportService().generate(report_type=type, audience=audience, language=language),
        request_id=request_id,
    )


@router.get("/trading-plan")
def trading_plan(request: Request, audience: str = Query("professional")):
    """Intraday Trading Plan report (Ch.10)."""
    request_id = getattr(request.state, "request_id", None)
    return success(ReportService().trading_plan(audience=audience), request_id=request_id)


@router.get("/patterns")
def patterns(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(AnalysisService().detect_patterns(), request_id=request_id)


@router.get("/technical")
def technical(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(AnalysisService().refresh_technical(), request_id=request_id)


@router.get("/{symbol}")
def market_by_symbol(symbol: str, request: Request):
    """Canonical market intelligence for an asset (Ch.18 §18.7 / §18.25)."""
    request_id = getattr(request.state, "request_id", None)
    from src.services.integration import IntegrationService

    data = IntegrationService().market_intelligence(symbol)
    if data is None:
        from src.api.responses import failure

        return failure(
            "Requested asset is not supported.",
            code="INVALID_SYMBOL",
            request_id=request_id,
            status_code=404,
        )
    return success(data, request_id=request_id)
