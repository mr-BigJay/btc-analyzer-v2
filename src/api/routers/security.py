"""Security API (Ch.19)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from src.api.deps import enforce_role
from src.api.responses import failure, success
from src.api_spec.contracts import ApiRole
from src.config import settings
from src.services.security import SecurityService

router = APIRouter(prefix="/api/v1/security", tags=["security"])


@router.get("/status")
def security_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(SecurityService().status(), request_id=request_id)


@router.get("/posture")
def security_posture(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(SecurityService().posture(), request_id=request_id)


@router.get("/checklist")
def security_checklist(request: Request):
    request_id = getattr(request.state, "request_id", None)
    https = (request.headers.get("x-forwarded-proto") or request.url.scheme) == "https"
    return success(SecurityService().checklist(https_enforced=https), request_id=request_id)


@router.get("/audit")
def security_audit(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    action: str | None = None,
):
    """Audit trail — Operator+ when auth enabled."""
    request_id = getattr(request.state, "request_id", None)
    principal = getattr(request.state, "principal", None)
    if settings.api_auth_enabled:
        if principal is None:
            return failure("Authentication required", code="UNAUTHORIZED", request_id=request_id, status_code=401)
        denied = enforce_role(principal, ApiRole.OPERATOR.value, request)
        if denied is not None:
            from src.security.audit import audit_trail
            from src.security.contracts import AuditAction

            audit_trail.append(
                AuditAction.PERMISSION_DENIED,
                actor=principal.subject,
                role=principal.role,
                outcome="denied",
                resource="/api/v1/security/audit",
                request_id=request_id or "",
            )
            return denied
    rows = SecurityService().audit(limit=limit, action=action)
    return success({"audit": rows, "count": len(rows)}, request_id=request_id)
