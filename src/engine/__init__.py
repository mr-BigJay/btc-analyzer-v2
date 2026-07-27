"""AI Layer — Layer 7 (Ch.2 §2.4).

AI never replaces raw data — it interprets validated evidence (Ch.2 §2.2).
Decision Engine is the ONLY component allowed to generate trading recommendations (Rule 6).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core import AnalysisObject, ModuleResult, ProbabilityObject, utc_now_iso
from src.core.contracts import NarrativeObject


@dataclass
class DecisionBundle:
    """Inputs to the Decision Engine — never mutated by engines."""

    narrative: ModuleResult[NarrativeObject] | None = None
    futures: AnalysisObject | None = None
    options: AnalysisObject | None = None
    technical: AnalysisObject | None = None
    patterns: AnalysisObject | None = None
    structure: AnalysisObject | None = None


@dataclass
class DecisionResult:
    """AI Decision Engine output before ProbabilityObject packaging."""

    bias: str = "neutral"
    layer_results: list[AnalysisObject] = field(default_factory=list)
    rationale: str = ""
    risk_flags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)

    @property
    def confirming_engines(self) -> list[str]:
        if self.bias == "neutral":
            return []
        return [r.engine for r in self.layer_results if r.bias == self.bias]

    @property
    def is_recommendation_eligible(self) -> bool:
        """Never trust one module alone (Ch.2 §2.5 Decision Engine)."""
        return (
            self.bias in ("bullish", "bearish")
            and len(self.confirming_engines) >= 3
            and not any(f.startswith("BLOCK:") for f in self.risk_flags)
        )


class AnalysisEngine:
    """Optional orchestrator placeholder — Layer 6 engines remain independent."""

    def collect_verdicts(self, bundle: DecisionBundle) -> list[AnalysisObject]:
        verdicts: list[AnalysisObject] = []
        for item in (
            bundle.futures,
            bundle.options,
            bundle.technical,
            bundle.patterns,
            bundle.structure,
        ):
            if item is not None:
                verdicts.append(item)
        return verdicts


class ProbabilityEngine:
    """Converts DecisionResult into ProbabilityObject (Ch.2 §2.6)."""

    def estimate(self, decision: DecisionResult) -> ModuleResult[ProbabilityObject]:
        raise NotImplementedError("Awaiting Design Book Chapter 3+")


class DecisionEngine:
    """Merges every analysis result. Never trusts one module alone."""

    def __init__(self) -> None:
        self.analysis = AnalysisEngine()
        self.probability = ProbabilityEngine()

    def evaluate(self, bundle: DecisionBundle) -> ModuleResult[ProbabilityObject]:
        raise NotImplementedError("Awaiting Design Book Chapter 3+")
