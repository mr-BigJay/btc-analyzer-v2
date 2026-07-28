"""FastAPI auth dependencies (Ch.18)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from src.api.responses import failure
from src.api_spec.auth import authenticate_headers, require_role
from src.api_spec.contracts import ApiRole, Principal
from src.api_spec.observability import api_metrics
from src.config import settings


def _header_map(
    authorization: str | None,
    x_api_key: str | None,
) -> dict[str, str]:
    h: dict[str, str] = {}
    if authorization:
        h["Authorization"] = authorization
    if x_api_key:
        h["X-API-Key"] = x_api_key
    return h


async def get_principal(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> Principal | None:
    principal = authenticate_headers(_header_map(authorization, x_api_key))
    request.state.principal = principal
    return principal


async def optional_auth(principal: Principal | None = Depends(get_principal)) -> Principal | None:
    return principal


async def require_auth(request: Request, principal: Principal | None = Depends(get_principal)) -> Principal:
    if not settings.api_auth_enabled:
        # Auth optional globally — anonymous Viewer
        return principal or Principal(subject="anonymous", role=ApiRole.VIEWER.value, auth_method="none")
    if principal is None:
        api_metrics.record_auth_failure()
        # Raise via HTTPException-like response handled by caller — use Request flag
        request.state.auth_error = failure(
            "Authentication required",
            code="UNAUTHORIZED",
            request_id=getattr(request.state, "request_id", None),
            status_code=401,
        )
        raise AuthRequired()
    return principal


class AuthRequired(Exception):
    """Signal that auth failed; routers may catch or middleware handles."""


def enforce_role(principal: Principal, minimum: str, request: Request):
    if settings.api_auth_enabled and not require_role(principal, minimum):
        return failure(
            "Insufficient permissions",
            code="FORBIDDEN",
            request_id=getattr(request.state, "request_id", None),
            status_code=403,
        )
    return None
