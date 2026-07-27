"""Publication decision rules (Ch.9 §9.15)."""

from __future__ import annotations

from src.config import settings


def publication_gate(
    *,
    data_quality_score: float,
    confidence_score: float,
    composites_ok: bool = True,
    validation_errors: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """
    Before publishing any analysis:
    - DQS above minimum
    - Composites calculated
    - No critical validation errors
    - Confidence above threshold OR elevated uncertainty stated
    """
    notes: list[str] = []
    errors = list(validation_errors or [])
    min_dqs = float(getattr(settings, "scoring_min_dqs", 60.0))
    min_conf = float(getattr(settings, "scoring_min_confidence", 55.0))

    publish = True
    if not composites_ok:
        publish = False
        notes.append("Composite scores incomplete — publication suppressed")
    if errors:
        publish = False
        notes.append("Critical validation errors present — publication suppressed")
    if data_quality_score < min_dqs:
        publish = False
        notes.append(
            f"Data Quality Score {data_quality_score:.0f} below minimum {min_dqs:.0f} — "
            "recommendations suppressed (insufficient data quality)"
        )
    if confidence_score < min_conf:
        # May still publish with explicit elevated uncertainty
        notes.append(
            f"Confidence {confidence_score:.0f} below publication threshold {min_conf:.0f} — "
            "report must state elevated uncertainty"
        )
        # Still allow publish=True with uncertainty note (per §9.15)
    return publish, notes
