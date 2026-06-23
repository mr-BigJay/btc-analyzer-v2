from fastapi import APIRouter, HTTPException

from src.db.models import get_session
from src.options.pipeline import OptionsPipeline
from src.options.service import OptionsService

router = APIRouter(prefix="/api/v1/options", tags=["options"])
options_service = OptionsService()


@router.get("/latest")
def options_latest():
    session = get_session()
    try:
        return options_service.get_latest(session)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        session.close()


@router.get("/screener")
def options_screener():
    """Returns latest auto-collected screener data."""
    session = get_session()
    try:
        return options_service.get_screener(session)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        session.close()


@router.get("/risk-profile")
def options_risk_profile():
    """Returns latest auto-computed risk profile."""
    session = get_session()
    try:
        return options_service.get_risk_profile(session)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        session.close()


@router.get("/status")
def options_status():
    from src.config import settings

    session = get_session()
    try:
        snap = OptionsPipeline.get_latest(session)
        return {
            "deribit_configured": settings.deribit_configured,
            "currency": settings.deribit_currency,
            "auto_collection": True,
            "has_data": snap is not None,
            "last_updated": snap["updated_at"] if snap else None,
            "mode": snap["mode"] if snap else None,
        }
    finally:
        session.close()
