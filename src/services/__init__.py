"""Service layer facades (Ch.5 §5.6) — modules communicate via interfaces only."""

from src.services.analysis import AnalysisService
from src.services.collection import CollectionService
from src.services.decision import DecisionService
from src.services.intelligence import IntelligenceService
from src.services.market import MarketService

__all__ = [
    "CollectionService",
    "AnalysisService",
    "IntelligenceService",
    "DecisionService",
    "MarketService",
]
