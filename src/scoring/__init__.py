"""Scoring & Decision Model package (Ch.9)."""

from src.scoring.contracts import DecisionObject

__all__ = ["DecisionObject", "ScoringEngine"]


def __getattr__(name: str):
    if name == "ScoringEngine":
        from src.scoring.engine import ScoringEngine

        return ScoringEngine
    raise AttributeError(name)
