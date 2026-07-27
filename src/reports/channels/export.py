"""Export writers — JSON / Markdown / CSV (Ch.10 §10.14)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.config import settings
from src.reports.channels.markdown import render_markdown
from src.reports.contracts import CanonicalReport


def export_dir() -> Path:
    path = settings.data_dir / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_report(
    report: CanonicalReport | dict[str, Any],
    *,
    formats: list[str] | None = None,
    audience: str = "professional",
    language: str = "en",
) -> dict[str, str]:
    data = report.to_dict() if isinstance(report, CanonicalReport) else dict(report)
    meta = data.get("metadata") or {}
    report_id = meta.get("report_id") or "report"
    stamp = str(data.get("generated_at") or "").replace(":", "-")
    base = export_dir() / f"{report_id}_{stamp}"
    formats = formats or ["json", "markdown"]
    written: dict[str, str] = {}

    if "json" in formats:
        path = Path(str(base) + ".json")
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        written["json"] = str(path)

    if "markdown" in formats or "md" in formats:
        path = Path(str(base) + ".md")
        path.write_text(render_markdown(data, audience=audience, language=language), encoding="utf-8")
        written["markdown"] = str(path)

    if "csv" in formats:
        path = Path(str(base) + ".csv")
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["field", "value"])
            for key in (
                "report_type",
                "generated_at",
                "market_bias",
                "confidence",
                "market_regime",
                "market_narrative",
                "executive_summary",
                "final_conclusion",
            ):
                writer.writerow([key, data.get(key)])
            for i, d in enumerate(data.get("key_drivers") or []):
                writer.writerow([f"key_driver_{i+1}", d])
            for i, r in enumerate(data.get("risk_factors") or []):
                writer.writerow([f"risk_factor_{i+1}", r])
        written["csv"] = str(path)

    # PDF placeholder note — generate markdown sibling for print workflows
    if "pdf" in formats and "markdown" not in written:
        path = Path(str(base) + ".md")
        path.write_text(render_markdown(data, audience=audience, language=language), encoding="utf-8")
        written["pdf_source_markdown"] = str(path)

    return written
