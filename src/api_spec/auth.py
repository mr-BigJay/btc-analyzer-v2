"""Authentication & authorization (Ch.18 §18.12–§18.13)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from src.api_spec.contracts import ROLE_RANK, ApiRole, Principal
from src.config import settings


def parse_api_keys() -> dict[str, str]:
    """Map api_key -> role from settings.api_keys (key or key:Role)."""
    out: dict[str, str] = {}
    raw = (settings.api_keys or "").strip()
    if not raw:
        return out
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            key, role = part.split(":", 1)
            out[key.strip()] = role.strip() or ApiRole.VIEWER.value
        else:
            out[part] = ApiRole.ANALYST.value
    return out


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def issue_jwt(
    *,
    subject: str,
    role: str = ApiRole.ANALYST.value,
    ttl_sec: int | None = None,
    secret: str | None = None,
) -> str:
    """Issue HS256 JWT (thin, stdlib-only)."""
    secret = secret or settings.api_jwt_secret
    ttl = ttl_sec if ttl_sec is not None else int(settings.api_jwt_ttl_sec)
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": subject, "role": role, "iat": now, "exp": now + ttl}
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url(sig)}"


def verify_jwt(token: str, *, secret: str | None = None) -> dict[str, Any] | None:
    secret = secret or settings.api_jwt_secret
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h, p, s = parts
        expected = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(s)):
            return None
        payload = json.loads(_b64url_decode(p))
        if int(payload.get("exp") or 0) < int(time.time()):
            return None
        return payload
    except Exception:  # noqa: BLE001
        return None


def authenticate_headers(headers: dict[str, str] | Any) -> Principal | None:
    """Resolve principal from Authorization / X-API-Key. Returns None if absent."""
    get = headers.get if isinstance(headers, dict) else lambda k, d=None: headers.get(k, d)
    api_key = get("X-API-Key") or get("x-api-key")
    if api_key:
        keys = parse_api_keys()
        if api_key in keys:
            return Principal(subject=f"key:{api_key[:6]}…", role=keys[api_key], auth_method="api_key")
        # If auth disabled and no keys configured, treat any key as Viewer for local/dev? No — reject.
        return None

    auth = get("Authorization") or get("authorization") or ""
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        payload = verify_jwt(token)
        if payload:
            return Principal(
                subject=str(payload.get("sub") or "jwt"),
                role=str(payload.get("role") or ApiRole.VIEWER.value),
                auth_method="jwt",
            )
        return None
    return None


def require_role(principal: Principal | None, minimum: str) -> bool:
    if principal is None:
        return False
    return principal.has_at_least(minimum)


def effective_rate_limit(principal: Principal | None) -> int:
    if principal and principal.auth_method != "none":
        return int(settings.api_rate_limit_authenticated)
    return int(settings.api_rate_limit_per_minute)
