"""Roadmap, Future Evolution & AI Governance contracts (Ch.23)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

GOVERNANCE_SCHEMA_VERSION = "1.0"
GOVERNANCE_ENGINE_VERSION = "1.0"


class MaturityStage(str, Enum):
    FOUNDATION = "Foundation"
    OPERATIONAL = "Operational"
    INTELLIGENT = "Intelligent"
    ADAPTIVE = "Adaptive"
    ENTERPRISE = "Enterprise"


class ChangeLifecycle(str, Enum):
    PROPOSAL = "Proposal"
    TECHNICAL_REVIEW = "Technical Review"
    VALIDATION = "Validation"
    APPROVAL = "Approval"
    DEPLOYMENT = "Deployment"
    MONITORING = "Monitoring"
    CONTINUOUS_IMPROVEMENT = "Continuous Improvement"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class PromptRecord:
    """Production prompt registry entry (Ch.23 §23.8)."""

    prompt_id: str
    version: str
    author: str
    effective_date: str
    review_history: list[str] = field(default_factory=list)
    compatibility_notes: str = ""
    status: str = "active"
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceObject:
    """Standard Governance Object summarizing AI + roadmap posture (Ch.23)."""

    vision: str = "AI-native Market Intelligence Platform"
    maturity_stage: str = MaturityStage.OPERATIONAL.value
    ai_advisory_only: bool = True
    human_in_the_loop: bool = True
    explainability_required: bool = True
    prompt_registry_versioned: bool = True
    plugin_architecture: str = "planned"
    current_release_line: str = "1.0"
    next_milestone: str = "1.5"
    schema_version: str = GOVERNANCE_SCHEMA_VERSION
    last_updated: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


STRATEGIC_PRINCIPLES = [
    "Backward compatibility whenever practical",
    "Explainability before complexity",
    "Modular architecture",
    "AI as an analytical assistant, not an autonomous decision maker",
    "Evidence-based conclusions",
    "Continuous improvement through measurable feedback",
]

ROADMAP = {
    "1.0": {
        "name": "Foundation Release",
        "status": "current",
        "features": [
            "Spot Analysis",
            "Futures Analysis",
            "Options Analysis",
            "Liquidity Intelligence",
            "Volatility Layer",
            "Daily Outlook",
            "Intraday Trading Plan",
            "REST API",
            "Dashboard",
        ],
    },
    "1.5": {
        "name": "Platform Expansion",
        "status": "planned",
        "features": [
            "Multi-asset support",
            "Portfolio dashboard",
            "Custom watchlists",
            "Enhanced alert engine",
            "Strategy templates",
        ],
    },
    "2.0": {
        "name": "Intelligent Analytics",
        "status": "planned",
        "features": [
            "Multi-agent AI architecture",
            "Quantitative factor engine",
            "Historical scenario comparison",
            "Strategy simulation",
            "AI memory",
            "Advanced explainability",
        ],
    },
    "3.0": {
        "name": "Institutional Platform",
        "status": "planned",
        "features": [
            "Plugin ecosystem",
            "Multi-user collaboration",
            "Enterprise administration",
            "Advanced permissions",
            "Cloud-native deployment",
            "External AI providers",
        ],
    },
}

PLUGIN_CATEGORIES = [
    "Exchange adapters",
    "New indicators",
    "Risk models",
    "AI providers",
    "Portfolio analytics",
    "Macroeconomic feeds",
    "Alternative data sources",
]

FUTURE_ASSETS = [
    "Ethereum",
    "Solana",
    "BNB",
    "XRP",
    "Gold",
    "Equity Index Futures",
    "Commodities",
    "Foreign Exchange",
    "Tokenized Assets",
]

AI_GOVERNANCE_REQUIREMENTS = [
    "Human-readable reasoning",
    "Version-controlled prompts",
    "Version-controlled model configuration",
    "Traceable analytical evidence",
    "Deterministic output structure",
    "Continuous validation",
]

EXPLAINABILITY_REQUIREMENTS = [
    "Supporting evidence",
    "Influential indicators",
    "Layer agreement",
    "Confidence rationale",
    "Alternative scenarios",
]

HUMAN_IN_THE_LOOP_ACTIONS = [
    "Prompt updates",
    "Model replacement",
    "Feature approval",
    "Analytical policy changes",
    "Major release approval",
]

MODEL_EVOLUTION = [
    "Larger language models",
    "Domain-specialized models",
    "Ensemble reasoning",
    "Multi-agent collaboration",
    "Retrieval-Augmented Generation (RAG)",
    "Hybrid symbolic reasoning",
]

DRIFT_SIGNALS = [
    "Confidence distribution changes",
    "Output consistency",
    "Validation failures",
    "Historical replay divergence",
    "User feedback trends",
]

KNOWLEDGE_ARTIFACTS = [
    "Market concepts",
    "Indicator definitions",
    "Historical events",
    "Risk policies",
    "AI prompt versions",
    "Analytical heuristics",
]

FEEDBACK_DRIVERS = [
    "Historical replay",
    "Prediction evaluation",
    "Operational metrics",
    "User feedback",
    "AI validation",
    "Incident reviews",
]

GOVERNANCE_LIFECYCLE = [stage.value for stage in ChangeLifecycle]

DOCUMENTATION_UPDATES = [
    "Architecture documentation",
    "API documentation",
    "Data contracts",
    "Prompt registry",
    "Operational procedures",
    "Testing documentation",
]

TECH_DEBT_GUIDELINES = [
    "Record architectural debt",
    "Prioritize high-risk items",
    "Review debt each release cycle",
    "Avoid hidden complexity",
    "Allocate engineering capacity for refactoring",
]

SUCCESS_METRICS = {
    "Platform Availability": "≥ 99.9%",
    "Data Quality Score": "≥ 98",
    "AI Validation Pass Rate": "≥ 95%",
    "Alert Precision": "Continuous improvement",
    "Average API Latency": "< 250 ms",
    "Deployment Success Rate": "≥ 99%",
}

MATURITY_MODEL = {
    MaturityStage.FOUNDATION.value: "Core analysis and reporting",
    MaturityStage.OPERATIONAL.value: "Stable production platform",
    MaturityStage.INTELLIGENT.value: "Advanced AI-assisted analysis",
    MaturityStage.ADAPTIVE.value: "Self-improving analytical workflows",
    MaturityStage.ENTERPRISE.value: "Extensible multi-tenant platform",
}

ARCHITECTURAL_SEPARATIONS = [
    "Data acquisition",
    "Feature engineering",
    "Analytical reasoning",
    "AI interpretation",
    "Decision support",
    "Presentation",
    "Operations",
]

ENDURING_PRINCIPLES = [
    "Architecture over implementation",
    "Explainability over opacity",
    "Reliability over novelty",
    "Security over convenience",
    "Measured evolution over uncontrolled growth",
    "Human oversight over autonomous action",
    "Continuous learning through measurable outcomes",
]

LONG_TERM_ARCHITECTURE_PRINCIPLES = [
    "Modular by default",
    "Observable by design",
    "Secure by design",
    "Explainable AI",
    "API-first integration",
    "Backward compatibility",
    "Evidence-driven evolution",
]
