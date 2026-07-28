"""Quality Assurance API (Ch.22)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from src.api.responses import success
from src.services.qa import QAService

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])


@router.get("/status")
def qa_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(QAService().status(), request_id=request_id)


@router.get("/report")
def qa_report(request: Request):
    request_id = getattr(request.state, "request_id", None)
    # Build report from live suite evaluation
    suite = QAService().suite(include_stress=False)
    return success(suite.get("test_report") or QAService().report(), request_id=request_id)


@router.get("/gates")
def qa_gates(request: Request):
    request_id = getattr(request.state, "request_id", None)
    suite = QAService().suite(include_stress=False)
    return success(suite.get("gates") or QAService().gates(), request_id=request_id)


@router.get("/suite")
def qa_suite(request: Request, stress: bool = Query(False)):
    request_id = getattr(request.state, "request_id", None)
    return success(QAService().suite(include_stress=stress), request_id=request_id)


@router.get("/performance")
def qa_performance(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(QAService().performance(), request_id=request_id)


@router.get("/security")
def qa_security(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(QAService().security(), request_id=request_id)


@router.get("/resilience")
def qa_resilience(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(QAService().resilience(), request_id=request_id)


@router.get("/replay")
def qa_replay(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(QAService().replay(), request_id=request_id)


@router.get("/defects")
def qa_defects(request: Request, limit: int = Query(50, ge=1, le=200)):
    request_id = getattr(request.state, "request_id", None)
    return success(QAService().defects(limit=limit), request_id=request_id)
