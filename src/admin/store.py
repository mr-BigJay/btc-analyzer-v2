"""Persistent admin config + auth store."""

from __future__ import annotations

import json
import os
import secrets
import threading
from pathlib import Path
from typing import Any

from src.admin.contracts import EDITABLE_FIELDS
from src.config import BASE_DIR, settings
from src.security.accounts import hash_password, verify_password

_lock = threading.RLock()


def admin_dir() -> Path:
    path = settings.data_dir / "admin"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _config_path() -> Path:
    return admin_dir() / "config.json"


def _auth_path() -> Path:
    return admin_dir() / "auth.json"


def _sessions_path() -> Path:
    return admin_dir() / "sessions.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_overrides() -> dict[str, Any]:
    with _lock:
        data = _read_json(_config_path(), {})
        return data if isinstance(data, dict) else {}


def save_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        current = load_overrides()
        for k, v in overrides.items():
            if k.startswith("_") or k in EDITABLE_FIELDS:
                current[k] = v
        current["schema_version"] = "1.0"
        _write_json(_config_path(), current)
        return current


def apply_overrides_to_runtime(overrides: dict[str, Any] | None = None) -> None:
    """Hot-apply saved overrides onto settings + process env."""
    data = overrides if overrides is not None else load_overrides()
    for key, value in data.items():
        if key.startswith("_") or key == "schema_version":
            continue
        meta = EDITABLE_FIELDS.get(key)
        if not meta:
            continue
        env_name = meta.get("env") or key.upper()
        if value is None:
            continue
        if isinstance(value, bool):
            os.environ[env_name] = "true" if value else "false"
        else:
            os.environ[env_name] = str(value)
        attr = meta.get("attr")
        if attr and hasattr(settings, attr):
            typ = meta.get("type")
            casted: Any = value
            if typ == "bool":
                casted = bool(value) if isinstance(value, bool) else str(value).lower() in {"1", "true", "yes", "on"}
            elif typ == "int":
                casted = int(value)
            elif typ == "float":
                casted = float(value)
            else:
                casted = value
            object.__setattr__(settings, attr, casted)


def sync_dotenv(overrides: dict[str, Any] | None = None) -> bool:
    """Merge overrides into project .env for restart persistence (best-effort)."""
    data = overrides if overrides is not None else load_overrides()
    env_path = BASE_DIR / ".env"
    try:
        existing: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if not line.strip() or line.strip().startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                existing[k.strip()] = v
        for key, value in data.items():
            meta = EDITABLE_FIELDS.get(key)
            if not meta:
                continue
            env_name = meta.get("env") or key.upper()
            if isinstance(value, bool):
                existing[env_name] = "true" if value else "false"
            else:
                existing[env_name] = str(value)
        lines = [f"{k}={v}" for k, v in existing.items()]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def is_setup_complete() -> bool:
    auth = _read_json(_auth_path(), {})
    return bool(auth.get("password_hash"))


def set_admin_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("password_too_short")
    with _lock:
        _write_json(
            _auth_path(),
            {
                "password_hash": hash_password(password),
                "created": True,
            },
        )


def verify_admin_password(password: str) -> bool:
    auth = _read_json(_auth_path(), {})
    hashed = auth.get("password_hash")
    if not hashed:
        return False
    return verify_password(password, hashed)


def create_session() -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        sessions = _read_json(_sessions_path(), {})
        if not isinstance(sessions, dict):
            sessions = {}
        sessions[token] = True
        # keep last 20
        if len(sessions) > 20:
            keys = list(sessions.keys())[:-20]
            for k in keys:
                sessions.pop(k, None)
        _write_json(_sessions_path(), sessions)
    return token


def revoke_session(token: str | None) -> None:
    if not token:
        return
    with _lock:
        sessions = _read_json(_sessions_path(), {})
        if isinstance(sessions, dict) and token in sessions:
            sessions.pop(token, None)
            _write_json(_sessions_path(), sessions)


def valid_session(token: str | None) -> bool:
    if not token:
        return False
    sessions = _read_json(_sessions_path(), {})
    return isinstance(sessions, dict) and bool(sessions.get(token))


# Apply persisted overrides at import time
apply_overrides_to_runtime()
