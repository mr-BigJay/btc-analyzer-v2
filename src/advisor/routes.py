"""All advisor API routes (insight + dashboard setup)."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.advisor.agent_tasks import create_task, list_tasks
from src.advisor.service import AdvisorService
from src.advisor.settings_store import to_public_dict, update_from_request
from src.config import settings

router = APIRouter(prefix="/api/v1/advisor", tags=["advisor"])

advisor_service = AdvisorService()


class AdvisorSettingsUpdate(BaseModel):
    advisor_enabled: bool | None = None
    advisor_api_key: str | None = None
    advisor_api_base: str | None = None
    advisor_model: str | None = None
    advisor_cache_minutes: int | None = Field(default=None, ge=1, le=1440)
    advisor_telegram_enabled: bool | None = None
    advisor_telegram_proactive: bool | None = None
    advisor_chat_history_limit: int | None = Field(default=None, ge=2, le=50)
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


class AdvisorTestRequest(BaseModel):
    advisor_api_key: str | None = None
    advisor_api_base: str | None = None
    advisor_model: str | None = None


def _get_session():
    from src.db.models import get_session

    return get_session()


@router.get("/settings")
def get_advisor_settings():
    return to_public_dict()


@router.put("/settings")
@router.post("/settings")
def save_advisor_settings(body: AdvisorSettingsUpdate):
    try:
        return update_from_request(body.model_dump(exclude_none=True))
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.post("/settings/test")
def test_advisor_settings(body: AdvisorTestRequest | None = None):
    api_key = (body.advisor_api_key if body and body.advisor_api_key else None) or settings.advisor_api_key
    api_base = (body.advisor_api_base if body and body.advisor_api_base else None) or settings.advisor_api_base
    model = (body.advisor_model if body and body.advisor_model else None) or settings.advisor_model

    if not api_key:
        raise HTTPException(400, "API key is required")

    if not api_base.startswith("http"):
        raise HTTPException(400, "API Base URL bayad ba http:// ya https:// shoro beshe")

    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 20,
        "messages": [
            {"role": "user", "content": "Reply with exactly: OK"},
        ],
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        return {
            "ok": True,
            "message": "اتصال موفق بود",
            "model": model,
            "reply_preview": (content or "")[:80],
        }
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:200] if exc.response else str(exc)
        raise HTTPException(400, f"API error: {detail}") from exc
    except Exception as exc:
        raise HTTPException(400, f"Connection failed: {exc}") from exc


@router.get("")
def advisor_insight(refresh: bool = False):
    if not settings.advisor_enabled:
        return {"enabled": False, "message": "Advisor is disabled"}

    session = _get_session()
    try:
        if refresh:
            insight = advisor_service.generate(session, force=True)
        else:
            insight = advisor_service.get_latest(session)
            if not insight:
                insight = advisor_service.generate(session, force=True)
        return advisor_service.to_dict(insight)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    finally:
        session.close()


@router.get("/tasks")
def advisor_tasks(limit: int = 20):
    return {"tasks": list_tasks(limit=limit)}
