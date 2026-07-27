"""AI Layer — Layer 7 Decision Engine (Ch.2 §2.4 / Ch.7).

AI never replaces raw data — it interprets validated Analysis Engine output.
Never accesses raw exchange feeds directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.ai.engine import AIDecisionEngine
from src.analysis.contracts import MarketAnalysisOutput
from src.core import AnalysisObject, ModuleResult, ModuleStatus, ProbabilityObject, utc_now_iso
from src.core.contracts import NarrativeObject


@dataclass
class DecisionBundle:
    """Legacy adapter inputs — prefer MarketAnalysisOutput (Ch.6→7)."""

    narrative: ModuleResult[NarrativeObject] | None = None
    futures: AnalysisObject | None = None
    options: AnalysisObject | None = None
    technical: AnalysisObject | None = None
    patterns: AnalysisObject | None = None
    structure: AnalysisObject | None = None
    market_analysis: MarketAnalysisOutput | dict[str, Any] | None = None


@dataclass
class DecisionResult:
    """AI Decision Engine output before ProbabilityObject packaging."""

    bias: str = "neutral"
    layer_results: list[AnalysisObject] = field(default_factory=list)
    rationale: str = ""
    risk_flags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    report: dict[str, Any] = field(default_factory=dict)

    @property
    def confirming_engines(self) -> list[str]:
        if self.bias == "neutral":
            return []
        return [r.engine for r in self.layer_results if r.bias == self.bias]

    @property
    def is_recommendation_eligible(self) -> bool:
        """Never trust one module alone (Ch.2 §2.5 Decision Engine)."""
        return (
            self.bias in ("bullish", "bearish", "Bullish", "Bearish")
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
    """Converts DecisionResult into ProbabilityObject (Ch.7 §7.8)."""

    def estimate(self, decision: DecisionResult) -> ModuleResult[ProbabilityObject]:
        report = decision.report or {}
        scenarios = report.get("scenarios") or []
        dist = report.get("probability_distribution") or {}
        bull = float(dist.get("trend_continuation") or 50) / 100.0
        bear = float(dist.get("trend_reversal") or 50) / 100.0
        total = bull + bear or 1.0
        obj = ProbabilityObject(
            bullish_probability=bull / total,
            bearish_probability=bear / total,
            confidence=float(report.get("confidence") or 0) / 100.0,
            preferred_direction=(report.get("trading_plan") or {}).get("preferred_direction", "no_trade"),
            confirming_layers=[
                e.get("layer") for e in report.get("evidence") or [] if "Bullish" in str(e.get("signal"))
            ],
            conflicting_layers=[
                e.get("layer") for e in report.get("evidence") or [] if "Bearish" in str(e.get("signal"))
            ],
            risk_flags=list(report.get("major_risks") or []),
            rationale=str((report.get("reasoning") or {}).get("primary_conclusion") or decision.rationale),
            scenarios=scenarios,
        )
        return ModuleResult(
            module="probability_engine",
            status=ModuleStatus.OK,
            confidence=float(report.get("confidence") or 50),
            data=obj,
        )


class DecisionEngine:
    """Ch.7 AI Decision Engine facade — merges analysis into explainable intelligence."""

    def __init__(self) -> None:
        self.analysis = AnalysisEngine()
        self.probability = ProbabilityEngine()
        self.ai = AIDecisionEngine()

    def evaluate(self, bundle: DecisionBundle | None = None) -> ModuleResult[ProbabilityObject]:
        analysis = bundle.market_analysis if bundle else None
        report = self.ai.decide(analysis=analysis, persist=True)
        decision = DecisionResult(
            bias=report.market_bias,
            rationale=report.reasoning.get("primary_conclusion", ""),
            risk_flags=list(report.major_risks),
            report=report.to_dict(),
        )
        return self.probability.estimate(decision)

    def decide(self, analysis: MarketAnalysisOutput | dict[str, Any] | None = None, **kwargs: Any):
        return self.ai.decide(analysis=analysis, **kwargs)
