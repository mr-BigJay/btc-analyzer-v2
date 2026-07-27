"""Standard API response envelope (Ch.5 §5.7)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi.responses import JSONResponse


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def success(
    data: Any = None,
    *,
    request_id: str | None = None,
    status_code: int = 200,
) -> JSONResponse:
    body = {
        "status": "success",
        "timestamp": utc_now_iso(),
        "request_id": request_id or str(uuid4()),
        "data": data if data is not None else {},
    }
    return JSONResponse(content=body, status_code=status_code)


def failure(
    message: str,
    *,
    code: str = "ERROR",
    request_id: str | None = None,
    details: Any = None,
    status_code: int = 400,
) -> JSONResponse:
    body = {
        "status": "error",
        "timestamp": utc_now_iso(),
        "request_id": request_id or str(uuid4()),
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }
    return JSONResponse(content=body, status_code=status_code)
