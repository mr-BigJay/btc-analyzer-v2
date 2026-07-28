"""Risk Management Engine (Ch.15) — deterministic, AI-independent."""

from __future__ import annotations

from typing import Any

from src.cache.keys import CacheKeys
from src.logging_setup import get_logger
from src.risk.categories import (
    score_data_risk,
    score_event_risk,
    score_execution_risk,
    score_leverage_risk,
    score_liquidity_risk,
    score_market_risk,
    score_stop_noise,
    score_volatility_risk,
)
from src.risk.contracts import RiskObject
from src.risk.crs import composite_risk_score
from src.risk.explain import build_risk_explanation, risk_reward_assessment
from src.risk.matrix import confidence_risk_guidance
from src.risk.no_trade import evaluate_no_trade_zone
from src.risk.sizing import refine_exposure, sizing_guidance_text
from src.storage.redis_cache import redis_cache

log = get_logger("risk.engine")


class RiskEngine:
    """Independent execution-risk layer (Ch.15). AI cannot override outputs."""

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
    ) -> RiskObject:
        decision = decision or {}
        intelligence = intelligence or {}
        analysis = analysis or {}
        context = context or {}

        feature_dq = None
        if isinstance(context.get("feature_data_quality"), (int, float)):
            feature_dq = float(context["feature_data_quality"])
        elif isinstance(decision.get("features"), dict) and decision["features"].get("data_quality") is not None:
            feature_dq = float(decision["features"]["data_quality"])

        market = score_market_risk(intelligence=intelligence, analysis=analysis, decision=decision)
        liquidity = score_liquidity_risk(intelligence=intelligence, analysis=analysis, context=context)
        volatility = score_volatility_risk(intelligence=intelligence, analysis=analysis)
        leverage = score_leverage_risk(intelligence=intelligence, analysis=analysis, decision=decision)
        event = score_event_risk(
            macro_event=macro_event, near_options_expiry=near_options_expiry, intelligence=intelligence
        )
        data = score_data_risk(decision=decision, analysis=analysis, feature_dq=feature_dq)
        execution = score_execution_risk(liquidity=liquidity, volatility=volatility, event=event)
        stop = score_stop_noise(volatility=volatility, liquidity=liquidity, analysis=analysis)

        categories = {
            "market": market,
            "liquidity": liquidity,
            "volatility": volatility,
            "leverage": leverage,
            "event": event,
            "data": data,
            "execution": execution,
        }
        crs, level, parts = composite_risk_score(categories)

        ntz, ntz_reasons = evaluate_no_trade_zone(
            decision=decision,
            intelligence=intelligence,
            analysis=analysis,
            crs=crs,
            data_risk_score=data.score,
            event_risk_label=event.label,
            liquidity_label=liquidity.label,
            macro_event=macro_event,
            exchange_degraded=exchange_degraded,
            unresolved_validation=unresolved_validation,
        )

        confidence = float(decision.get("confidence_score") or analysis.get("confidence") or 50)
        dqs = float(decision.get("data_quality_score") or 80)
        exposure_label, fraction, capital_mode = refine_exposure(
            crs=crs,
            confidence=confidence,
            msi=str(intelligence.get("market_stress_index") or ""),
            dqs=dqs,
            volatility_adjustment=volatility.label,
            no_trade=ntz,
        )

        # Unfavorable RR suppresses recommendations
        rr = risk_reward_assessment(crs=crs, confidence=confidence, no_trade=ntz)
        suppression_log: list[str] = []
        suppressed = False
        if ntz:
            suppressed = True
            suppression_log.extend(ntz_reasons)
        if rr == "Unfavorable" and not ntz:
            suppressed = True
            suppression_log.append("Risk-to-reward profile unfavorable")
            exposure_label, fraction, capital_mode = "No new position", 0.0, "Preservation"

        guidance = confidence_risk_guidance(confidence, crs)
        explanation = build_risk_explanation(
            crs=crs,
            risk_level=level,
            categories=categories,
            no_trade=ntz,
            no_trade_reasons=ntz_reasons,
            market_bias=str(decision.get("market_bias") or analysis.get("market_bias") or ""),
        )

        obj = RiskObject(
            composite_risk_score=crs,
            risk_level=level,
            liquidity_state=liquidity.label,
            volatility_adjustment=volatility.label,
            event_risk=event.label,
            leverage_environment=leverage.label,
            no_trade_zone=ntz,
            no_trade_reasons=ntz_reasons,
            capital_preservation_mode=capital_mode,
            suggested_exposure=exposure_label,
            exposure_fraction=fraction,
            stop_noise=stop.label,
            risk_reward=rr,
            confidence_risk_guidance=guidance,
            category_scores={k: v.to_dict() for k, v in categories.items()}
            | {"stop_noise": stop.to_dict(), "components": parts},
            explanation=explanation,
            suppressed=suppressed,
            suppression_log=suppression_log,
        )

        if persist:
            redis_cache.set(CacheKeys.LATEST_RISK_OBJECT, obj.to_dict(), ttl_sec=3600)
            if suppressed:
                redis_cache.set(
                    "latest_risk_suppression",
                    {"reasons": suppression_log, "crs": crs, "generated_at": obj.generated_at},
                    ttl_sec=3600,
                )

        log.info(
            "risk crs={} level={} ntz={} exposure={} suppressed={}",
            crs,
            level,
            ntz,
            exposure_label,
            suppressed,
        )
        return obj

    def apply_to_trading_plan(self, plan: dict[str, Any], risk: RiskObject) -> dict[str, Any]:
        """Enforce risk controls on a trading plan dict — AI cannot bypass."""
        out = dict(plan)
        out["risk_object"] = risk.to_dict()
        out["position_sizing_guidance"] = sizing_guidance_text(
            risk.suggested_exposure, risk.exposure_fraction, risk.capital_preservation_mode
        )
        if risk.no_trade_zone or risk.suppressed or risk.exposure_fraction <= 0:
            out["preferred_direction"] = "no_trade"
            reason = "; ".join(risk.suppression_log or risk.no_trade_reasons) or risk.explanation
            note = f"Risk Engine override: {reason}"
            out["session_notes"] = ((out.get("session_notes") or "") + " " + note).strip()
            out["confirmation_conditions"] = list(out.get("confirmation_conditions") or []) + [
                "CRS / No Trade Zone must clear before engagement",
                f"Require CRS ≤ 60 (current {risk.composite_risk_score})",
            ]
        return out
