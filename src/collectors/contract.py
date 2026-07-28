"""Internal data contract for normalized collection messages (Ch.12 §12.21)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = "1.0"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def stamp_timestamps(
    payload: dict[str, Any],
    *,
    exchange_timestamp: str | None = None,
    collection_timestamp: str | None = None,
    processing_timestamp: str | None = None,
) -> dict[str, Any]:
    """Attach exchange / collection / processing timestamp triad (Ch.12 §12.9)."""
    out = dict(payload)
    now = utc_now_iso()
    out["exchange_timestamp"] = exchange_timestamp or out.get("exchange_timestamp") or out.get("timestamp") or now
    out["collection_timestamp"] = collection_timestamp or out.get("collection_timestamp") or now
    out["processing_timestamp"] = processing_timestamp or now
    # Canonical timestamp remains ISO-8601 UTC for downstream consumers
    if not out.get("timestamp"):
        out["timestamp"] = out["exchange_timestamp"]
    return out


def stamp_contract(
    payload: dict[str, Any],
    *,
    source: str,
    market: str,
    asset: str | None = None,
    sequence: int | None = None,
    schema_version: str = SCHEMA_VERSION,
) -> dict[str, Any]:
    """Build immutable-within-version internal message (Ch.12 §12.21)."""
    stamped = stamp_timestamps(payload)
    return {
        "source": source,
        "asset": str(asset or stamped.get("symbol") or "BTCUSDT").upper().replace("-", "").replace("_", ""),
        "market": market,
        "timestamp": stamped.get("timestamp") or stamped["exchange_timestamp"],
        "exchange_timestamp": stamped["exchange_timestamp"],
        "collection_timestamp": stamped["collection_timestamp"],
        "processing_timestamp": stamped["processing_timestamp"],
        "sequence": sequence if sequence is not None else int(uuid4().int % 1_000_000_000),
        "payload": {
            k: v
            for k, v in stamped.items()
            if k
            not in {
                "source",
                "asset",
                "market",
                "timestamp",
                "exchange_timestamp",
                "collection_timestamp",
                "processing_timestamp",
                "sequence",
                "schema_version",
                "payload",
            }
        },
        "schema_version": schema_version,
    }


def latency_ms(contract: dict[str, Any]) -> float | None:
    """Collection latency = collection_ts − exchange_ts (ms)."""
    try:
        ex = datetime.fromisoformat(str(contract["exchange_timestamp"]).replace("Z", "+00:00"))
        col = datetime.fromisoformat(str(contract["collection_timestamp"]).replace("Z", "+00:00"))
        return max(0.0, (col - ex).total_seconds() * 1000.0)
    except Exception:  # noqa: BLE001
        return None
