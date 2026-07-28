"""Service layer facades (Ch.5 §5.6) — modules communicate via interfaces only."""

from src.services.analysis import AnalysisService
from src.services.collection import CollectionService
from src.services.dashboard import DashboardService
from src.services.decision import DecisionService
from src.services.deploy import DeployService
from src.services.events import EventService
from src.services.features import FeatureService
from src.services.integration import IntegrationService
from src.services.intelligence import IntelligenceService
from src.services.market import MarketService
from src.services.reports import ReportService
from src.services.risk import RiskService
from src.services.scoring import ScoringService
from src.services.security import SecurityService
from src.services.validation import ValidationService

__all__ = [
    "CollectionService",
    "FeatureService",
    "AnalysisService",
    "IntelligenceService",
    "ScoringService",
    "DecisionService",
    "ReportService",
    "MarketService",
    "ValidationService",
    "RiskService",
    "EventService",
    "DashboardService",
    "IntegrationService",
    "SecurityService",
    "DeployService",
]
