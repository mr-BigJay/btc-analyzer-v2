"""Risk Management service facade (Ch.15)."""

from __future__ import annotations

from typing import Any

from src.risk.contracts import RISK_ENGINE_VERSION, RISK_SCHEMA_VERSION
from src.risk.engine import RiskEngine
from src.storage.redis_cache import redis_cache


class RiskService:
    """Thin facade over the deterministic Risk Engine."""

    def __init__(self) -> None:
        self.engine = RiskEngine()

    def evaluate(
        self,
        *,
        decision: dict[str, Any] | None = None,
        intelligence: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        macro_event: bool = False,
        near_options_expiry: bool = False,
        exchange_degraded: bool = False,
        unresolved_validation: bool = False,
        persist: bool = True,
    ) -> dict[str, Any]:
        obj = self.engine.evaluate(
            decision=decision,
            intelligence=intelligence,
            analysis=analysis,
            context=context,
            macro_event=macro_event,
            near_options_expiry=near_options_expiry,
            exchange_degraded=exchange_degraded,
            unresolved_validation=unresolved_validation,
            persist=persist,
        )
        return obj.to_dict()

    def apply_to_trading_plan(self, plan: dict[str, Any], risk: dict[str, Any]) -> dict[str, Any]:
        from src.risk.contracts import RiskObject

        return self.engine.apply_to_trading_plan(plan, RiskObject.from_dict(risk))

    def latest(self) -> dict[str, Any] | None:
        from src.cache.keys import CacheKeys

        cached = redis_cache.get(CacheKeys.LATEST_RISK_OBJECT)
        if not isinstance(cached, dict):
            cached = redis_cache.get("latest_risk_object")
        return cached if isinstance(cached, dict) else None

    def status(self) -> dict[str, Any]:
        latest = self.latest() or {}
        return {
            "schema_version": RISK_SCHEMA_VERSION,
            "engine_version": RISK_ENGINE_VERSION,
            "has_cached_object": bool(latest),
            "composite_risk_score": latest.get("composite_risk_score"),
            "risk_level": latest.get("risk_level"),
            "no_trade_zone": latest.get("no_trade_zone"),
            "categories": [
                "market",
                "liquidity",
                "volatility",
                "leverage",
                "event",
                "data",
                "execution",
            ],
            "crs_bands": {
                "0-20": "Very Low",
                "21-40": "Low",
                "41-60": "Moderate",
                "61-80": "High",
                "81-100": "Extreme",
            },
            "governance": [
                "deterministic",
                "reproducible",
                "ai_cannot_override",
                "suppression_logged",
            ],
        }
