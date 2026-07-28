"""Dashboard, Visualization & User Experience package (Ch.17)."""

from src.dashboard.contracts import DASHBOARD_SCHEMA_VERSION, DashboardState, DashboardView, Personalization
from src.dashboard.engine import DashboardEngine

__all__ = [
    "DashboardEngine",
    "DashboardView",
    "DashboardState",
    "Personalization",
    "DASHBOARD_SCHEMA_VERSION",
]
