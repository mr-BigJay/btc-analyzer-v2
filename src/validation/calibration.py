"""Confidence & probability calibration (Ch.14 §14.12–§14.13)."""

from __future__ import annotations

from typing import Any, Sequence

from src.validation.contracts import CalibrationLabel


CONFIDENCE_BINS = (
    (90, 100, "90–100"),
    (80, 89, "80–89"),
    (70, 79, "70–79"),
    (60, 69, "60–69"),
    (0, 59, "0–59"),
)


def confidence_bin(confidence: float) -> str:
    c = float(confidence)
    for lo, hi, label in CONFIDENCE_BINS:
        if lo <= c <= hi:
            return label
    return "0–59"


def calibration_table(
    pairs: Sequence[tuple[float, bool]],
) -> dict[str, Any]:
    """pairs = (confidence, was_correct)."""
    buckets: dict[str, list[bool]] = {label: [] for _, _, label in CONFIDENCE_BINS}
    for conf, ok in pairs:
        buckets[confidence_bin(conf)].append(bool(ok))

    table: dict[str, Any] = {}
    gaps = []
    for lo, hi, label in CONFIDENCE_BINS:
        vals = buckets[label]
        if not vals:
            table[label] = {"n": 0, "accuracy": None, "expected_mid": (lo + hi) / 2, "gap": None}
            continue
        acc = 100.0 * sum(vals) / len(vals)
        mid = (lo + hi) / 2
        gap = abs(acc - mid)
        gaps.append(gap)
        table[label] = {"n": len(vals), "accuracy": round(acc, 1), "expected_mid": mid, "gap": round(gap, 1)}

    avg_gap = sum(gaps) / len(gaps) if gaps else 100.0
    if avg_gap <= 5:
        label = CalibrationLabel.EXCELLENT.value
    elif avg_gap <= 10:
        label = CalibrationLabel.GOOD.value
    elif avg_gap <= 18:
        label = CalibrationLabel.MODERATE.value
    else:
        label = CalibrationLabel.POOR.value

    return {"bins": table, "label": label, "avg_gap": round(avg_gap, 2) if gaps else None}


def probability_calibration(
    pairs: Sequence[tuple[float, bool]],
    *,
    bin_width: float = 10.0,
) -> dict[str, Any]:
    """If predicted probability≈70%, ~70% should succeed (Ch.14 §14.12)."""
    buckets: dict[int, list[bool]] = {}
    for prob, ok in pairs:
        key = int(float(prob) // bin_width) * int(bin_width)
        buckets.setdefault(key, []).append(bool(ok))
    out = {}
    gaps = []
    for key, vals in sorted(buckets.items()):
        acc = 100.0 * sum(vals) / len(vals)
        expected = key + bin_width / 2
        gap = abs(acc - expected)
        gaps.append(gap)
        out[f"{key}-{key + int(bin_width)}"] = {
            "n": len(vals),
            "accuracy": round(acc, 1),
            "expected": expected,
            "gap": round(gap, 1),
        }
    return {"bins": out, "avg_gap": round(sum(gaps) / len(gaps), 2) if gaps else None}
