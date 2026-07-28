"""Prompt registry and version governance (Ch.23 §23.8)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from src.config import settings
from src.governance.contracts import PromptRecord, utc_now_iso


def prompt_registry_dir() -> Path:
    path = settings.data_dir / "governance" / "prompts"
    path.mkdir(parents=True, exist_ok=True)
    return path


# Seeded production prompts (deterministic NLG templates — advisory only)
_DEFAULT_PROMPTS = [
    PromptRecord(
        prompt_id="daily_outlook.narrative",
        version="1.0.0",
        author="architecture",
        effective_date="2026-01-01",
        review_history=["2026-01-01: initial foundation release"],
        compatibility_notes="Requires Analysis + Scoring contracts schema 1.0",
        summary="Daily outlook narrative assembly from evidence blocks",
    ),
    PromptRecord(
        prompt_id="trading_plan.structure",
        version="1.0.0",
        author="architecture",
        effective_date="2026-01-01",
        review_history=["2026-01-01: initial foundation release"],
        compatibility_notes="Advisory DSS plan only — no execution",
        summary="Intraday trading plan structure from scenarios + risk",
    ),
    PromptRecord(
        prompt_id="explainability.reasoning_block",
        version="1.0.0",
        author="architecture",
        effective_date="2026-01-01",
        review_history=["2026-01-01: initial foundation release"],
        compatibility_notes="Must accompany every AI conclusion",
        summary="Explainability ReasoningBlock builder guidance",
    ),
]


class PromptRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._memory: dict[str, PromptRecord] = {p.prompt_id: p for p in _DEFAULT_PROMPTS}

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._memory.values()]

    def get(self, prompt_id: str) -> dict[str, Any] | None:
        with self._lock:
            p = self._memory.get(prompt_id)
            return p.to_dict() if p else None

    def register(self, record: PromptRecord, *, persist: bool = True) -> dict[str, Any]:
        """Register/update a prompt — human review required for production activation."""
        with self._lock:
            existing = self._memory.get(record.prompt_id)
            if existing:
                history = list(existing.review_history)
                history.append(f"{utc_now_iso()}: updated to {record.version} by {record.author}")
                record.review_history = history or record.review_history
            self._memory[record.prompt_id] = record
        if persist:
            path = prompt_registry_dir() / f"{record.prompt_id.replace('.', '_')}_{record.version}.json"
            path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        return record.to_dict()

    def requires_human_review(self, prompt_id: str, new_version: str) -> bool:
        current = self.get(prompt_id)
        if not current:
            return True
        return current.get("version") != new_version


prompt_registry = PromptRegistry()
