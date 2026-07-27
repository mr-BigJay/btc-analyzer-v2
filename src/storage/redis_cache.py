"""Redis cache layer with in-process fallback (Ch.4 §4.2 / §4.11)."""

from __future__ import annotations

import json
import logging
from typing import Any

from src.config import settings
from src.storage.cache import MemoryCache, global_cache

logger = logging.getLogger(__name__)


class RedisCache:
    """Hot-data cache. Falls back to MemoryCache when Redis is unavailable."""

    def __init__(self, memory: MemoryCache | None = None) -> None:
        self.memory = memory or global_cache
        self._client = None
        self._enabled = bool(settings.redis_url)
        if self._enabled:
            try:
                import redis

                self._client = redis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1.5,
                    socket_timeout=1.5,
                )
                self._client.ping()
                logger.info("Redis cache connected: %s", settings.redis_url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Redis unavailable (%s) — using memory cache", exc)
                self._client = None

    @property
    def backend(self) -> str:
        return "redis" if self._client is not None else "memory"

    def set(self, key: str, value: Any, ttl_sec: int | None = None) -> None:
        self.memory.set(key, value)
        if self._client is None:
            return
        try:
            payload = json.dumps(value, ensure_ascii=False, default=str)
            if ttl_sec:
                self._client.setex(key, ttl_sec, payload)
            else:
                self._client.set(key, payload)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis set failed: %s", exc)

    def get(self, key: str) -> Any | None:
        if self._client is not None:
            try:
                raw = self._client.get(key)
                if raw is not None:
                    return json.loads(raw)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Redis get failed: %s", exc)
        return self.memory.get(key)

    def delete(self, key: str) -> None:
        self.memory.delete(key)
        if self._client is None:
            return
        try:
            self._client.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis delete failed: %s", exc)

    def snapshot(self) -> dict[str, Any]:
        return {"backend": self.backend, "memory_keys": list(self.memory.snapshot().keys())}


# Process singleton
redis_cache = RedisCache()
