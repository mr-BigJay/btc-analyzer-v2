"""Position sizing / exposure guidance (Ch.15 §15.6). Guidance only."""

from __future__ import annotations

from typing import Any

from src.risk.contracts import CapitalMode, ExposureBand, VolatilityAdjustment


def exposure_from_crs(crs: float) -> tuple[str, float]:
    s = float(crs)
    if s <= 20:
        return ExposureBand.FULL.value, 1.0
    if s <= 40:
        return ExposureBand.MODERATE.value, 0.65
    if s <= 60:
        return ExposureBand.REDUCED.value, 0.40
    if s <= 80:
        return ExposureBand.MINIMAL.value, 0.20
    return ExposureBand.NONE.value, 0.0


def apply_volatility_adjustment(fraction: float, volatility_adjustment: str) -> float:
    adj = {
        VolatilityAdjustment.NEUTRAL.value: 1.0,
        VolatilityAdjustment.SLIGHT_REDUCTION.value: 0.9,
        VolatilityAdjustment.NONE.value: 1.0,
        VolatilityAdjustment.REDUCED.value: 0.7,
        VolatilityAdjustment.SIGNIFICANT_REDUCTION.value: 0.4,
    }.get(volatility_adjustment, 1.0)
    return max(0.0, min(1.0, fraction * adj))


def refine_exposure(
    *,
    crs: float,
    confidence: float,
    msi: str | None,
    dqs: float,
    volatility_adjustment: str,
    no_trade: bool,
) -> tuple[str, float, str]:
    """Return (exposure_label, fraction, capital_mode)."""
    if no_trade:
        return ExposureBand.NONE.value, 0.0, CapitalMode.LOCKDOWN.value

    label, frac = exposure_from_crs(crs)
    frac = apply_volatility_adjustment(frac, volatility_adjustment)

    # Confidence soft gate
    if confidence < 55:
        frac *= 0.5
    elif confidence < 65:
        frac *= 0.75

    # MSI escalation
    if msi in ("High", "Extreme"):
        frac = 0.0
        label = ExposureBand.NONE.value
    elif msi == "Elevated":
        frac *= 0.6

    # DQS soft gate
    if dqs < 60:
        frac *= 0.5
    if dqs < 50:
        frac = 0.0
        label = ExposureBand.NONE.value

    frac = round(max(0.0, min(1.0, frac)), 3)
    if frac <= 0:
        label = ExposureBand.NONE.value
        mode = CapitalMode.LOCKDOWN.value if (msi in ("High", "Extreme") or dqs < 50) else CapitalMode.PRESERVATION.value
    elif frac < 0.25:
        label = ExposureBand.MINIMAL.value
        mode = CapitalMode.PRESERVATION.value
    elif frac < 0.45:
        label = ExposureBand.REDUCED.value
        mode = CapitalMode.REDUCED.value
    elif frac < 0.75:
        label = ExposureBand.MODERATE.value
        mode = CapitalMode.NORMAL.value
    else:
        label = ExposureBand.FULL.value
        mode = CapitalMode.NORMAL.value
    return label, frac, mode


def sizing_guidance_text(exposure_label: str, fraction: float, capital_mode: str) -> str:
    if fraction <= 0:
        return f"Flat — {exposure_label}. Capital mode: {capital_mode}."
    pct = int(round(fraction * 100))
    return (
        f"Suggested exposure: {exposure_label} (~{pct}% of strategy risk unit). "
        f"Capital mode: {capital_mode}. Guidance only — not account enforcement."
    )
