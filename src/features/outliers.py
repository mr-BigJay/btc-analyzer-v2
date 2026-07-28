"""Outlier detection — flag, do not silently remove (Ch.13 §13.16)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OutlierFlag:
    field: str
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "code": self.code, "message": self.message}


def detect_outliers(payload: dict[str, Any]) -> list[OutlierFlag]:
    flags: list[OutlierFlag] = []

    for key in ("price", "mark_price", "spot_price", "close"):
        val = payload.get(key)
        if val is None:
            continue
        try:
            fv = float(val)
        except (TypeError, ValueError):
            flags.append(OutlierFlag(key, "TYPE", f"{key} not numeric"))
            continue
        if fv <= 0:
            flags.append(OutlierFlag(key, "NEGATIVE_PRICE", f"{key}={fv}"))
        if fv != fv or fv in (float("inf"), float("-inf")):
            flags.append(OutlierFlag(key, "NON_FINITE", f"{key} non-finite"))

    fr = payload.get("funding_rate")
    if fr is not None:
        try:
            ff = float(fr)
            if abs(ff) > 0.05:  # >5% funding is extreme
                flags.append(OutlierFlag("funding_rate", "FUNDING_SPIKE", f"funding={ff}"))
        except (TypeError, ValueError):
            flags.append(OutlierFlag("funding_rate", "TYPE", "funding_rate not numeric"))

    vol = payload.get("volume") or payload.get("relative_volume")
    if vol is not None:
        try:
            vv = float(vol)
            if vv < 0:
                flags.append(OutlierFlag("volume", "NEGATIVE_VOLUME", f"volume={vv}"))
            if payload.get("volume_spike_score") is not None and float(payload["volume_spike_score"]) >= 0.95:
                flags.append(OutlierFlag("volume", "VOLUME_SPIKE", "sudden volume spike"))
        except (TypeError, ValueError):
            pass

    ts = payload.get("timestamp")
    if ts is not None and isinstance(ts, str) and "T" not in ts and not ts.isdigit():
        flags.append(OutlierFlag("timestamp", "TIMESTAMP", f"anomalous timestamp={ts}"))

    return flags
