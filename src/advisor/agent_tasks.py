"""Queue fix/improvement requests from Telegram for the Cursor agent."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import BASE_DIR

logger = logging.getLogger(__name__)

TASKS_DIR = BASE_DIR / "data" / "agent_tasks"


def _ensure_dir() -> None:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)


def create_task(
    *,
    user_message: str,
    source: str = "telegram",
    context: dict[str, Any] | None = None,
    chat_id: str = "",
) -> dict[str, Any]:
    _ensure_dir()
    task_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    payload = {
        "id": task_id,
        "status": "pending",
        "source": source,
        "chat_id": chat_id,
        "user_message": user_message.strip(),
        "context": context or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "instructions_for_cursor": (
            "این درخواست از ربات تلگرام BTC Analyzer آمده. "
            "مشکل را بررسی کن، در صورت نیاز کد را اصلاح کن، و نتیجه را به کاربر گزارش بده."
        ),
    }
    path = TASKS_DIR / f"{task_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Agent task created: %s", task_id)
    return payload


def list_tasks(limit: int = 20) -> list[dict[str, Any]]:
    _ensure_dir()
    files = sorted(TASKS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    tasks: list[dict[str, Any]] = []
    for path in files[:limit]:
        try:
            tasks.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return tasks


def format_task_summary(task: dict[str, Any]) -> str:
    ctx = task.get("context") or {}
    ov = (ctx.get("overview") or {}) if isinstance(ctx, dict) else {}
    problems = []
    if isinstance(ctx, dict):
        advisor = ctx.get("advisor") or {}
        if isinstance(advisor, dict):
            problems = advisor.get("problems") or []

    lines = [
        f"🆔 <b>{task.get('id', '—')}</b>",
        f"📅 {task.get('created_at', '—')[:19].replace('T', ' ')} UTC",
        "",
        f"📝 <b>درخواست:</b>\n{task.get('user_message', '—')}",
    ]
    if problems:
        lines.append("")
        lines.append("⚠️ <b>مشکلات داشبورد:</b>")
        for p in problems[:4]:
            lines.append(f"• {p}")
    if ov.get("price"):
        lines.append("")
        lines.append(
            f"💰 BTC: ${ov.get('price'):,.0f} | "
            f"امتیاز: {ov.get('overall_score', '—')} | "
            f"اعتماد: {ov.get('overall_confidence', '—')}%"
        )
    lines.append("")
    lines.append(
        "برای اصلاح در Cursor:\n"
        f"<code>data/agent_tasks/{task.get('id')}.json</code>"
    )
    return "\n".join(lines)
