"""API Specification & Integration package (Ch.18)."""

from src.api_spec.catalog import api_catalog
from src.api_spec.contracts import API_SCHEMA_VERSION, API_SPEC_VERSION, MarketIntelligenceResponse, Principal
from src.api_spec.market_contract import build_market_intelligence_response

__all__ = [
    "api_catalog",
    "API_SCHEMA_VERSION",
    "API_SPEC_VERSION",
    "MarketIntelligenceResponse",
    "Principal",
    "build_market_intelligence_response",
]
