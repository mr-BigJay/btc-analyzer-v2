"""Testing & Quality Assurance contracts (Ch.22)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

QA_SCHEMA_VERSION = "1.0"
QA_ENGINE_VERSION = "1.0"


class GateStatus(str, Enum):
    PASSED = "Passed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    PENDING = "Pending"


class OverallStatus(str, Enum):
    APPROVED = "Approved"
    BLOCKED = "Blocked"
    CONDITIONAL = "Conditional"


class DefectSeverity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class TestReport:
    """Standard Test Report (Ch.22 §22.24)."""

    __test__ = False  # prevent pytest collection

    release: str = "1.0.0"
    unit_tests: str = GateStatus.PENDING.value
    integration_tests: str = GateStatus.PENDING.value
    end_to_end_tests: str = GateStatus.PENDING.value
    performance: str = GateStatus.PENDING.value
    security: str = GateStatus.PENDING.value
    ai_validation: str = GateStatus.PENDING.value
    overall_status: str = OverallStatus.BLOCKED.value
    schema_version: str = QA_SCHEMA_VERSION
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


COVERAGE_TARGETS = {
    "Core Business Logic": 90,
    "Risk Engine": 95,
    "Feature Engineering": 90,
    "API Layer": 85,
    "Utility Modules": 80,
}

DEFECT_SEVERITIES = {
    DefectSeverity.CRITICAL.value: "Blocks production",
    DefectSeverity.HIGH.value: "Major functionality affected",
    DefectSeverity.MEDIUM.value: "Partial degradation",
    DefectSeverity.LOW.value: "Minor issue",
    DefectSeverity.INFORMATIONAL.value: "Improvement opportunity",
}

PIPELINE_STAGES = [
    "Source Code",
    "Static Analysis",
    "Unit Tests",
    "Integration Tests",
    "System Tests",
    "Performance Tests",
    "Security Tests",
    "AI Validation",
    "Release Approval",
]

PYRAMID_LAYERS = ["Unit Tests", "Integration", "E2E"]

RELEASE_GATES = [
    ("unit_tests", "Unit tests pass"),
    ("integration_tests", "Integration tests pass"),
    ("end_to_end_tests", "End-to-end scenarios pass"),
    ("security", "Security validation passes"),
    ("performance", "Performance targets are met"),
    ("migrations", "Database migrations succeed"),
    ("ai_validation", "AI validation passes"),
    ("critical_defects", "Critical defects are resolved"),
]

ACCEPTANCE_CRITERIA = [
    "Functional correctness",
    "Performance requirements",
    "Security requirements",
    "Documentation completeness",
    "Test coverage targets",
    "User acceptance criteria",
]

QUALITY_METRICS = [
    "Test success rate",
    "Defect density",
    "Mean time to detect",
    "Mean time to resolve",
    "Escaped defects",
    "Regression frequency",
    "Release stability",
]

TEST_DATA_CATEGORIES = [
    "Synthetic data",
    "Historical market data",
    "Edge-case scenarios",
    "Corrupted inputs",
    "High-volatility periods",
    "Low-liquidity periods",
]

RESILIENCE_SCENARIOS = [
    "Database unavailable",
    "Redis unavailable",
    "Exchange API timeout",
    "WebSocket disconnect",
    "AI service unavailable",
    "Disk nearing capacity",
]

PERFORMANCE_CHECKS = [
    "API throughput",
    "Dashboard responsiveness",
    "Collector latency",
    "Feature generation speed",
    "AI inference duration",
    "Database performance",
]

LOAD_SCENARIOS = {
    "High API traffic": "Scalability",
    "Multiple WebSocket clients": "Streaming capacity",
    "Concurrent collectors": "Data ingestion",
    "Simultaneous report generation": "Processing capacity",
}

APPROVAL_WORKFLOW = [
    "Development",
    "Automated Testing",
    "Quality Review",
    "Release Candidate",
    "Production Approval",
    "Deployment",
]
