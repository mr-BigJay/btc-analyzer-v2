"""Data Normalization stage (Ch.1 §1.7).

Converts validated exchange-specific payloads into a shared internal schema
so Analysis / Probability engines stay exchange-agnostic (modular principle).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class NormalizedSnapshot:
    """Canonical cross-source market snapshot for one analysis cycle."""

    symbol: str = "BTC"
    price: float | None = None
    narrative: dict = field(default_factory=dict)
    futures: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    technical: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    normalized_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DataNormalizer:
    """Maps validated source payloads into NormalizedSnapshot.

    Spec details arrive in later chapters.
    """

    def normalize(self, validated_payloads: dict[str, dict]) -> NormalizedSnapshot:
        raise NotImplementedError("Awaiting Design Book Chapter 2+")
