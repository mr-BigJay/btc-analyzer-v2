"""Governance / Roadmap API (Ch.23)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.responses import success
from src.services.governance import GovernanceService

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


@router.get("/status")
def governance_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(GovernanceService().status(), request_id=request_id)


@router.get("/object")
def governance_object(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(GovernanceService().governance_object(), request_id=request_id)


@router.get("/roadmap")
def governance_roadmap(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(GovernanceService().roadmap(), request_id=request_id)


@router.get("/prompts")
def governance_prompts(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(GovernanceService().prompts(), request_id=request_id)


@router.get("/ai")
def governance_ai(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(GovernanceService().ai(), request_id=request_id)


@router.get("/drift")
def governance_drift(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(GovernanceService().drift(), request_id=request_id)


@router.get("/maturity")
def governance_maturity(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(GovernanceService().maturity(), request_id=request_id)


@router.get("/lifecycle")
def governance_lifecycle_route(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(GovernanceService().lifecycle(), request_id=request_id)


@router.get("/architecture")
def governance_architecture(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(GovernanceService().architecture(), request_id=request_id)


@router.get("/debt")
def governance_debt(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(GovernanceService().tech_debt(), request_id=request_id)
