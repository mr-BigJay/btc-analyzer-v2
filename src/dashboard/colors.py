"""Semantic color mapping — color never sole carrier of meaning (Ch.17 §17.10)."""

from __future__ import annotations

from src.dashboard.contracts import SemanticColor


def bias_tone(bias: str) -> str:
    b = str(bias or "")
    if "Bull" in b:
        return SemanticColor.GREEN.value
    if "Bear" in b:
        return SemanticColor.RED.value
    if "Uncertain" in b or "Caution" in b:
        return SemanticColor.AMBER.value
    return SemanticColor.GRAY.value


def risk_tone(level: str | float | None) -> str:
    if isinstance(level, (int, float)):
        if level >= 81:
            return SemanticColor.RED.value
        if level >= 61:
            return SemanticColor.AMBER.value
        if level >= 41:
            return SemanticColor.BLUE.value
        return SemanticColor.GREEN.value
    s = str(level or "")
    if s in ("Extreme", "Critical", "High", "Extreme Risk", "High Risk"):
        return SemanticColor.RED.value if "Extreme" in s or "Critical" in s else SemanticColor.AMBER.value
    if s in ("Elevated", "Moderate", "Medium", "Elevated Risk", "Moderate Risk"):
        return SemanticColor.AMBER.value
    if s in ("Low", "Very Low", "Low Risk", "Informational"):
        return SemanticColor.GREEN.value
    return SemanticColor.GRAY.value


def severity_tone(severity: str) -> str:
    s = str(severity or "")
    if s in ("Critical", "High"):
        return SemanticColor.RED.value if s == "Critical" else SemanticColor.AMBER.value
    if s in ("Medium", "Elevated"):
        return SemanticColor.AMBER.value
    if s in ("Low", "Informational"):
        return SemanticColor.BLUE.value
    return SemanticColor.GRAY.value


def msi_tone(msi: str) -> str:
    if msi in ("Extreme", "High"):
        return SemanticColor.RED.value
    if msi in ("Elevated", "Moderate"):
        return SemanticColor.AMBER.value
    if msi == "Low":
        return SemanticColor.GREEN.value
    return SemanticColor.GRAY.value


def connection_tone(state: str) -> str:
    if state == "Live":
        return SemanticColor.GREEN.value
    if state in ("Stale", "Degraded"):
        return SemanticColor.AMBER.value
    if state in ("Offline", "Maintenance"):
        return SemanticColor.RED.value
    return SemanticColor.BLUE.value
