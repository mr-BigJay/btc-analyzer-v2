"""Account lockout and password hashing (Ch.19 §19.13)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any

from src.storage.redis_cache import redis_cache

LOCKOUT_KEY = "security:lockout:"
FAIL_KEY = "security:auth_fail:"
MAX_FAILURES = 5
LOCKOUT_SEC = 900  # 15 minutes


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """PBKDF2-HMAC-SHA256 adaptive hash (stdlib — no plaintext storage)."""
    salt_bytes = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 200_000)
    return f"pbkdf2_sha256$200000${salt_bytes.hex()}${dk.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, rounds, salt_hex, digest = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(dk.hex(), digest)
    except Exception:  # noqa: BLE001
        return False


def record_auth_failure(identity: str) -> dict[str, Any]:
    key = f"{FAIL_KEY}{identity}"
    raw = redis_cache.get(key)
    count = int(raw or 0) + 1
    redis_cache.set(key, count, ttl_sec=LOCKOUT_SEC)
    locked = count >= MAX_FAILURES
    if locked:
        redis_cache.set(f"{LOCKOUT_KEY}{identity}", time.time() + LOCKOUT_SEC, ttl_sec=LOCKOUT_SEC)
    return {"failures": count, "locked": locked, "lockout_sec": LOCKOUT_SEC if locked else 0}


def clear_auth_failures(identity: str) -> None:
    redis_cache.set(f"{FAIL_KEY}{identity}", 0, ttl_sec=1)
    redis_cache.set(f"{LOCKOUT_KEY}{identity}", 0, ttl_sec=1)


def is_locked(identity: str) -> bool:
    until = redis_cache.get(f"{LOCKOUT_KEY}{identity}")
    if until is None:
        return False
    try:
        return float(until) > time.time()
    except (TypeError, ValueError):
        return False
