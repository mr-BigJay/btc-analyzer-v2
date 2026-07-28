"""Deployment / DevOps API (Ch.20)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.responses import success
from src.services.deploy import DeployService

router = APIRouter(prefix="/api/v1/deploy", tags=["deploy"])


@router.get("/status")
def deploy_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(DeployService().status(), request_id=request_id)


@router.get("/object")
def deploy_object(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(DeployService().deployment_object(), request_id=request_id)


@router.get("/checklist")
def deploy_checklist(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(DeployService().checklist(), request_id=request_id)


@router.get("/rollback")
def deploy_rollback(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(DeployService().rollback(), request_id=request_id)


@router.get("/health")
def deploy_health(request: Request):
    request_id = getattr(request.state, "request_id", None)
    data = DeployService().health()
    code = 200 if data.get("ok") else 503
    return success(data, request_id=request_id, status_code=code)
