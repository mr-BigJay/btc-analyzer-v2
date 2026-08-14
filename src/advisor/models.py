from dataclasses import dataclass, field


@dataclass
class AdvisorInsight:
    problems: list[str] = field(default_factory=list)
    ideas: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    watch_levels: list[dict] = field(default_factory=list)
    confidence_note: str = ""
    headline: str = ""
    source: str = "rules"
    model: str = ""
    generated_at: str = ""
