"""Admin engine — config view, setup progress, operational actions."""

from __future__ import annotations

from typing import Any

from src import __version__
from src.admin.contracts import EDITABLE_FIELDS, GROUPS, SETUP_STEPS, ADMIN_SCHEMA_VERSION
from src.admin.store import (
    apply_overrides_to_runtime,
    create_session,
    is_setup_complete,
    load_overrides,
    save_overrides,
    set_admin_password,
    sync_dotenv,
    verify_admin_password,
)
from src.config import settings
from src.deploy.probes import health_detailed
from src.security.secrets import mask_secrets


def _mask_value(key: str, value: Any) -> Any:
    meta = EDITABLE_FIELDS.get(key) or {}
    if meta.get("type") != "secret":
        return value
    if value in (None, "", False):
        return ""
    text = str(value)
    if len(text) <= 4:
        return "***"
    return text[:2] + "***" + text[-2:]


def _current_value(key: str) -> Any:
    overrides = load_overrides()
    if key in overrides:
        return overrides[key]
    meta = EDITABLE_FIELDS[key]
    attr = meta.get("attr")
    if attr and hasattr(settings, attr):
        return getattr(settings, attr)
    # site keys from env/overrides only
    import os

    env_name = meta.get("env") or key.upper()
    return os.getenv(env_name, "")


def config_view(*, reveal_secrets: bool = False) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {g: [] for g in GROUPS}
    for key, meta in EDITABLE_FIELDS.items():
        raw = _current_value(key)
        configured = bool(raw) if meta.get("type") == "secret" else raw not in (None, "")
        item = {
            "key": key,
            "label": meta["label"],
            "type": meta["type"],
            "group": meta["group"],
            "value": raw if (reveal_secrets or meta.get("type") != "secret") else _mask_value(key, raw),
            "configured": configured if meta.get("type") == "secret" else True,
            "has_value": bool(raw) if not isinstance(raw, bool) else True,
        }
        groups[meta["group"]].append(item)
    return {
        "schema_version": ADMIN_SCHEMA_VERSION,
        "groups": [{"id": gid, "title": title, "fields": groups[gid]} for gid, title in GROUPS.items()],
        "setup_complete": is_setup_complete(),
    }


def update_config(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in (payload or {}).items():
        meta = EDITABLE_FIELDS.get(key)
        if not meta:
            continue
        # Empty secret means "leave unchanged"
        if meta.get("type") == "secret" and (value is None or value == ""):
            continue
        typ = meta.get("type")
        if typ == "bool":
            cleaned[key] = bool(value) if isinstance(value, bool) else str(value).lower() in {"1", "true", "yes", "on"}
        elif typ == "int":
            cleaned[key] = int(value)
        elif typ == "float":
            cleaned[key] = float(value)
        else:
            cleaned[key] = value
    saved = save_overrides(cleaned)
    apply_overrides_to_runtime(saved)
    dotenv_ok = sync_dotenv(saved)
    return {
        "ok": True,
        "updated_keys": list(cleaned.keys()),
        "dotenv_synced": dotenv_ok,
        "config": config_view(),
        "note": "تغییرات اعمال شد. برای برخی سرویس‌های sidecar ممکن است راه‌اندازی مجدد لازم باشد.",
    }


def setup_progress() -> dict[str, Any]:
    steps = []
    jwt_default = settings.api_jwt_secret in {"btc-analyzer-dev-secret-change-me", "change-me-in-production"}
    api_ready = bool(settings.api_keys) or settings.api_auth_enabled
    exch = bool(settings.binance_api_key or settings.deribit_client_id or settings.bitunix_api_key)
    tg = bool(settings.telegram_bot_token and settings.telegram_chat_id)
    # first_run: mark done if any analysis artifact or override flag
    overrides = load_overrides()
    first_run_done = bool(overrides.get("_first_run_done"))

    checks = {
        "admin_password": is_setup_complete(),
        "jwt_secret": not jwt_default,
        "api_access": api_ready,
        "exchanges": exch,  # optional — counts as done if skipped via flag
        "telegram": tg,
        "first_run": first_run_done,
    }
    # optional steps can be skipped
    skipped = set(overrides.get("_skipped_steps") or [])
    for step in SETUP_STEPS:
        sid = step["id"]
        done = checks.get(sid, False) or sid in skipped
        optional = sid in {"exchanges", "telegram"}
        steps.append({**step, "done": done, "optional": optional})
    required_done = all(s["done"] or s["optional"] for s in steps if s["id"] != "first_run") and checks["admin_password"] and checks["jwt_secret"]
    return {
        "steps": steps,
        "completed": sum(1 for s in steps if s["done"]),
        "total": len(steps),
        "ready_for_production": bool(required_done and checks["admin_password"] and checks["jwt_secret"]),
        "setup_complete": is_setup_complete(),
    }


def bootstrap(password: str, *, initial_config: dict[str, Any] | None = None) -> dict[str, Any]:
    if is_setup_complete():
        return {"ok": False, "error": "already_setup"}
    set_admin_password(password)
    if initial_config:
        update_config(initial_config)
    token = create_session()
    return {"ok": True, "token": token, "progress": setup_progress()}


def login(password: str) -> dict[str, Any]:
    if not is_setup_complete():
        return {"ok": False, "error": "setup_required"}
    if not verify_admin_password(password):
        return {"ok": False, "error": "invalid_credentials"}
    return {"ok": True, "token": create_session()}


def skip_step(step_id: str) -> dict[str, Any]:
    if step_id not in {"exchanges", "telegram"}:
        return {"ok": False, "error": "not_skippable"}
    overrides = load_overrides()
    skipped = list(overrides.get("_skipped_steps") or [])
    if step_id not in skipped:
        skipped.append(step_id)
    save_overrides({"_skipped_steps": skipped})
    return {"ok": True, "progress": setup_progress()}


def mark_first_run_done() -> None:
    save_overrides({"_first_run_done": True})


def run_op(op: str) -> dict[str, Any]:
    op = (op or "").strip().lower()
    try:
        if op == "collect":
            from src.services import CollectionService

            result = CollectionService().run_full()
            return {"ok": bool(result.ok), "op": op, "warnings": result.warnings, "symbol": getattr(result.snapshot, "symbol", None)}
        if op == "analyze":
            from src.services import AnalysisService

            out = AnalysisService().run_full()
            mark_first_run_done()
            return {
                "ok": True,
                "op": op,
                "market_bias": out.get("market_bias"),
                "confidence": out.get("confidence"),
                "primary_scenario": out.get("primary_scenario"),
            }
        if op == "outlook":
            from src.services import ReportService

            out = ReportService().daily_outlook(audience="professional", persist=True, export=False)
            mark_first_run_done()
            return {
                "ok": True,
                "op": op,
                "report_type": out.get("report_type"),
                "market_bias": out.get("market_bias"),
                "summary": (out.get("executive_summary") or "")[:400],
            }
        if op == "health":
            return {"ok": True, "op": op, "health": health_detailed()}
        return {"ok": False, "error": "unknown_op", "op": op}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "op": op, "error": mask_secrets(str(exc))[:300]}


def admin_status() -> dict[str, Any]:
    health = health_detailed()
    return {
        "version": __version__,
        "schema_version": ADMIN_SCHEMA_VERSION,
        "setup_complete": is_setup_complete(),
        "progress": setup_progress(),
        "health": health,
        "product": "decision-support-system",
        "gui": True,
    }
