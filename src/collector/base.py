import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class BaseCollector:
    source_name: str = "base"

    def __init__(self) -> None:
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def ms_to_datetime(ms: int | float) -> datetime:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)
