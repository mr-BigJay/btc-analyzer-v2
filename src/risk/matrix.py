"""Confidence vs Risk matrix (Ch.15 §15.15)."""

from __future__ import annotations


def confidence_band(confidence: float) -> str:
    return "High" if float(confidence) >= 70 else "Low"


def risk_band_from_crs(crs: float) -> str:
    return "High" if float(crs) >= 61 else "Low"


def confidence_risk_guidance(confidence: float, crs: float) -> str:
    conf = confidence_band(confidence)
    risk = risk_band_from_crs(crs)
    matrix = {
        ("High", "Low"): "Favorable conditions",
        ("High", "High"): "Opportunity with elevated caution",
        ("Low", "Low"): "Wait for confirmation",
        ("Low", "High"): "Avoid new exposure",
    }
    return matrix[(conf, risk)]
