from fastapi import APIRouter, HTTPException, Query

from src.options.service import OptionsService

router = APIRouter(prefix="/api/v1/options", tags=["options"])
options_service = OptionsService()


@router.get("/screener")
def options_screener(
    timeframe: str = Query("1d", pattern="^(1h|4h|1d)$"),
    min_size: float = Query(0.5, ge=0),
    option_type: str | None = Query(None, pattern="^(call|put)$"),
    limit: int = Query(200, ge=10, le=500),
):
    try:
        return options_service.get_screener(
            timeframe=timeframe,
            min_size=min_size,
            option_type=option_type,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(502, f"Deribit error: {exc}") from exc


@router.get("/risk-profile")
def options_risk_profile(
    mode: str = Query("auto", pattern="^(auto|public|private|selected)$"),
    timeframe: str = Query("1d", pattern="^(1h|4h|1d)$"),
    min_size: float = Query(1.0, ge=0),
    instruments: str | None = Query(None, description="Comma-separated instrument names"),
):
    try:
        inst_list = [i.strip() for i in instruments.split(",") if i.strip()] if instruments else None
        return options_service.get_risk_profile(
            mode=mode,
            timeframe=timeframe,
            min_size=min_size,
            instruments=inst_list,
        )
    except Exception as exc:
        raise HTTPException(502, f"Risk profile error: {exc}") from exc


@router.get("/status")
def options_status():
    from src.config import settings

    return {
        "deribit_configured": settings.deribit_configured,
        "currency": settings.deribit_currency,
    }
