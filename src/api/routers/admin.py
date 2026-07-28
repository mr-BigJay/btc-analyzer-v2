"""Admin console API — configure & operate from the Persian GUI."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, Field

from src.admin.store import is_setup_complete, revoke_session, valid_session
from src.api.responses import failure, success
from src.services.admin import AdminService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class BootstrapBody(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    config: dict | None = None


class LoginBody(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class ConfigBody(BaseModel):
    values: dict = Field(default_factory=dict)


def _token(x_admin_token: str | None, authorization: str | None) -> str | None:
    if x_admin_token:
        return x_admin_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _require_admin(request: Request, token: str | None):
    request_id = getattr(request.state, "request_id", None)
    if not is_setup_complete():
        return failure(
            "ابتدا راه‌اندازی اولیه را از پنل انجام دهید",
            code="SETUP_REQUIRED",
            request_id=request_id,
            status_code=403,
        )
    if not valid_session(token):
        return failure("نشست مدیر نامعتبر است", code="ADMIN_UNAUTHORIZED", request_id=request_id, status_code=401)
    return None


@router.get("/status")
def admin_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(AdminService().status(), request_id=request_id)


@router.get("/progress")
def admin_progress(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return success(AdminService().progress(), request_id=request_id)


@router.post("/bootstrap")
def admin_bootstrap(body: BootstrapBody, request: Request):
    request_id = getattr(request.state, "request_id", None)
    out = AdminService().bootstrap(body.password, initial_config=body.config)
    if not out.get("ok"):
        return failure("راه‌اندازی قبلاً انجام شده", code="ALREADY_SETUP", request_id=request_id, status_code=409)
    return success(out, request_id=request_id)


@router.post("/login")
def admin_login(body: LoginBody, request: Request):
    request_id = getattr(request.state, "request_id", None)
    out = AdminService().login(body.password)
    if not out.get("ok"):
        code = out.get("error") or "LOGIN_FAILED"
        status = 403 if code == "setup_required" else 401
        return failure("ورود ناموفق", code=code.upper(), request_id=request_id, status_code=status)
    return success(out, request_id=request_id)


@router.post("/logout")
def admin_logout(
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    authorization: str | None = Header(default=None),
):
    request_id = getattr(request.state, "request_id", None)
    revoke_session(_token(x_admin_token, authorization))
    return success({"ok": True}, request_id=request_id)


@router.get("/config")
def admin_get_config(
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    authorization: str | None = Header(default=None),
):
    request_id = getattr(request.state, "request_id", None)
    denied = _require_admin(request, _token(x_admin_token, authorization))
    if denied is not None:
        return denied
    return success(AdminService().config(), request_id=request_id)


@router.put("/config")
def admin_put_config(
    body: ConfigBody,
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    authorization: str | None = Header(default=None),
):
    request_id = getattr(request.state, "request_id", None)
    denied = _require_admin(request, _token(x_admin_token, authorization))
    if denied is not None:
        return denied
    return success(AdminService().update_config(body.values), request_id=request_id)


@router.post("/skip/{step_id}")
def admin_skip(
    step_id: str,
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    authorization: str | None = Header(default=None),
):
    request_id = getattr(request.state, "request_id", None)
    denied = _require_admin(request, _token(x_admin_token, authorization))
    if denied is not None:
        return denied
    out = AdminService().skip(step_id)
    if not out.get("ok"):
        return failure("این مرحله قابل رد شدن نیست", code="NOT_SKIPPABLE", request_id=request_id, status_code=400)
    return success(out, request_id=request_id)


@router.post("/ops/{op}")
def admin_ops(
    op: str,
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    authorization: str | None = Header(default=None),
):
    request_id = getattr(request.state, "request_id", None)
    denied = _require_admin(request, _token(x_admin_token, authorization))
    if denied is not None:
        return denied
    out = AdminService().run_op(op)
    code = 200 if out.get("ok") else 400
    return success(out, request_id=request_id, status_code=code)
