"""Published API catalog & compatibility policy (Ch.18)."""

from __future__ import annotations

from typing import Any

from src.api_spec.contracts import (
    API_SCHEMA_VERSION,
    API_SPEC_VERSION,
    COMPATIBILITY_POLICY,
    HTTP_STATUS,
    RESOURCE_CATEGORIES,
)
from src.api_spec.webhooks import SUPPORTED_EVENTS


def api_catalog() -> dict[str, Any]:
    return {
        "spec_version": API_SPEC_VERSION,
        "schema_version": API_SCHEMA_VERSION,
        "base_path": "/api/v1/",
        "principles": [
            "RESTful",
            "JSON",
            "versioned",
            "stateless",
            "UTC timestamps",
            "correlation identifiers",
            "consistent naming",
        ],
        "resource_categories": RESOURCE_CATEGORIES,
        "http_status_codes": HTTP_STATUS,
        "authentication": ["API Key", "JWT Access Token", "Refresh Token"],
        "roles": ["Viewer", "Analyst", "Operator", "Administrator"],
        "rate_limits": {
            "public_per_minute": 120,
            "authenticated_per_minute": 600,
            "streaming": "connection-based",
        },
        "websocket": {
            "paths": ["/ws", "/api/v1/ws", "/ws/v1/market/{symbol}"],
            "streams": [
                "Live Price",
                "Market Intelligence",
                "Alerts",
                "Confidence Updates",
                "Market Regime Changes",
                "Data Quality Updates",
            ],
        },
        "webhooks": {
            "events": SUPPORTED_EVENTS,
            "delivery": "signed HTTPS POST",
        },
        "endpoints": [
            {"method": "GET", "path": "/api/v1/assets", "purpose": "List supported assets"},
            {"method": "GET", "path": "/api/v1/assets/{symbol}", "purpose": "Asset metadata"},
            {"method": "GET", "path": "/api/v1/market/{symbol}", "purpose": "Current market intelligence"},
            {"method": "GET", "path": "/api/v1/reports/daily/{symbol}", "purpose": "Daily Outlook"},
            {"method": "GET", "path": "/api/v1/reports/intraday/{symbol}", "purpose": "Intraday Trading Plan"},
            {"method": "GET", "path": "/api/v1/alerts", "purpose": "Active alerts"},
            {"method": "GET", "path": "/api/v1/system/health", "purpose": "Platform health"},
            {"method": "GET", "path": "/api/v1/integration/status", "purpose": "API specification status"},
            {"method": "GET", "path": "/api/v1/integration/metrics", "purpose": "API observability"},
            {"method": "POST", "path": "/api/v1/integration/auth/token", "purpose": "Issue JWT"},
            {"method": "POST", "path": "/api/v1/integration/webhooks", "purpose": "Register webhook"},
        ],
        "compatibility_policy": COMPATIBILITY_POLICY,
        "documentation": {
            "openapi": "/api/openapi.json",
            "swagger": "/api/docs",
            "redoc": "/api/redoc",
        },
        "sdk_guidelines": {
            "languages": ["Python", "JavaScript / TypeScript", "Go"],
            "rule": "SDKs must remain thin wrappers around the public API",
        },
        "governance": [
            "api_first",
            "stable_versioned_contracts",
            "stateless",
            "consistent_envelopes",
            "strong_validation",
            "observable",
            "interface_separated_from_business_logic",
        ],
    }
