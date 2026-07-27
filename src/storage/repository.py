"""Central Data Repository — Layer 5 Storage (Ch.2 §2.4).

Responsibilities:
  - Historical storage
  - Caching / snapshots (fault tolerance §2.9)
  - Time-series management

Design Rule 1: modules must not reach into each other's tables.
All persistence goes through this repository facade.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings
from src.db.models import get_session, init_db

logger = logging.getLogger(__name__)


class CentralRepository:
    """Single storage gateway for snapshots and historical records."""

    def __init__(self) -> None:
        self.cache_dir = settings.data_dir / "snapshots"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _snapshot_path(self, module: str) -> Path:
        safe = module.lower().replace(" ", "_")
        return self.cache_dir / f"{safe}.json"

    def save_snapshot(self, module: str, payload: dict[str, Any]) -> None:
        path = self._snapshot_path(module)
        envelope = {
            **payload,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.debug("Snapshot saved for %s → %s", module, path)

    def load_snapshot(self, module: str) -> dict[str, Any] | None:
        path = self._snapshot_path(module)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Corrupt snapshot for %s: %s", module, exc)
            return None

    def ensure_schema(self) -> None:
        init_db()

    def session(self):
        """ORM session for historical tables — do not bypass this facade."""
        return get_session()
