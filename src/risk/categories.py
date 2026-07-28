"""Independent risk category scores (Ch.15 §15.4)."""

from __future__ import annotations

from typing import Any

from src.risk.contracts import (
    CategoryScore,
    EventRisk,
    LeverageEnvironment,
    LiquidityState,
    StopNoise,
    VolatilityAdjustment,
)


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def score_market_risk(*, intelligence: dict[str, Any], analysis: dict[str, Any], decision: dict[str, Any]) -> CategoryScore:
    msi = str(intelligence.get("market_stress_index") or "")
    base = {"Low": 18, "Moderate": 40, "Elevated": 58, "High": 75, "Extreme": 90}.get(msi, 40)
    drivers = []
    if msi:
        drivers.append(f"MSI={msi}")
    if intelligence.get("transition_probability", 0) >= 60:
        base += 8
        drivers.append("Elevated regime transition probability")
    if analysis.get("conflicts"):
        base += 6
        drivers.append("Analytical layer conflicts")
    if str(analysis.get("market_bias")) == "High Uncertainty":
        base += 10
        drivers.append("High Uncertainty bias")
    return CategoryScore("market", _clamp(base), msi or "Moderate", drivers)


def score_liquidity_risk(*, intelligence: dict[str, Any], analysis: dict[str, Any], context: dict[str, Any] | None = None) -> CategoryScore:
    ctx = context or {}
    state = str(intelligence.get("liquidity_state") or "")
    score = 35.0
    drivers = []
    # Map Ch.8 liquidity intelligence labels onto Ch.15 liquidity states
    mapping = {
        "Healthy": (15, LiquidityState.HEALTHY.value),
        "Balanced": (22, LiquidityState.HEALTHY.value),
        "Acceptable": (35, LiquidityState.ACCEPTABLE.value),
        "Liquidity Both Sides": (38, LiquidityState.ACCEPTABLE.value),
        "Liquidity Above": (42, LiquidityState.ACCEPTABLE.value),
        "Liquidity Below": (42, LiquidityState.ACCEPTABLE.value),
        "Magnet Zone": (48, LiquidityState.ACCEPTABLE.value),
        "Thin": (65, LiquidityState.THIN.value),
        "Liquidity Vacuum": (88, LiquidityState.CRITICAL.value),
        "Critical": (90, LiquidityState.CRITICAL.value),
    }
    label = LiquidityState.ACCEPTABLE.value
    if state in mapping:
        score, label = mapping[state]
        drivers.append(f"Liquidity state={state}")
    elif state:
        drivers.append(f"Liquidity state={state} (unmapped → Acceptable)")
    # Order book proxies
    ob = ctx.get("order_book") if isinstance(ctx.get("order_book"), dict) else {}
    bids = ob.get("bids") or []
    asks = ob.get("asks") or []
    if bids and asks:
        try:
            spread = float(asks[0][0]) - float(bids[0][0])
            mid = (float(asks[0][0]) + float(bids[0][0])) / 2
            if mid > 0 and spread / mid > 0.0008:
                score += 12
                drivers.append("Wide bid/ask spread")
                if label == LiquidityState.HEALTHY.value:
                    label = LiquidityState.ACCEPTABLE.value
        except (TypeError, ValueError, IndexError):
            pass
    elif not bids and not asks:
        score += 8
        drivers.append("Order book unavailable")
    tags = {t for r in (analysis.get("layer_results") or []) for t in (r.get("tags") or [])}
    if "Sweep Probability" in tags:
        score += 8
        drivers.append("Nearby liquidity sweep risk")
    return CategoryScore("liquidity", _clamp(score), label, drivers)


def score_volatility_risk(*, intelligence: dict[str, Any], analysis: dict[str, Any]) -> CategoryScore:
    vol = str(intelligence.get("volatility_regime") or analysis.get("volatility") or "Normal")
    table = {
        "Very Low": (12, VolatilityAdjustment.NEUTRAL.value),
        "Low": (22, VolatilityAdjustment.SLIGHT_REDUCTION.value),
        "Normal": (35, VolatilityAdjustment.NONE.value),
        "Medium": (40, VolatilityAdjustment.NONE.value),
        "Elevated": (62, VolatilityAdjustment.REDUCED.value),
        "High": (72, VolatilityAdjustment.REDUCED.value),
        "Extreme": (90, VolatilityAdjustment.SIGNIFICANT_REDUCTION.value),
        "Expansion": (70, VolatilityAdjustment.REDUCED.value),
    }
    score, adj = table.get(vol, (40, VolatilityAdjustment.NONE.value))
    return CategoryScore("volatility", float(score), adj, [f"Volatility regime={vol}"])


def score_leverage_risk(*, intelligence: dict[str, Any], analysis: dict[str, Any], decision: dict[str, Any]) -> CategoryScore:
    tags = {t for r in (analysis.get("layer_results") or []) for t in (r.get("tags") or [])}
    score = 30.0
    drivers = []
    crowded = "Overcrowded Market" in tags or "Long Squeeze Risk" in tags or "Short Squeeze Risk" in tags
    if crowded:
        score += 25
        drivers.append("Crowded leveraged positioning")
    feats = decision.get("features") if isinstance(decision.get("features"), dict) else {}
    if intelligence.get("derivatives_thesis"):
        score += 5
        drivers.append("Active derivatives thesis")
    for key in ("funding_trend", "crowded_trade_score", "leveraged_pressure"):
        val = feats.get(key)
        if isinstance(val, (int, float)) and abs(float(val)) >= 60:
            score += 12
            drivers.append(f"{key} elevated ({float(val):.0f})")
        elif isinstance(val, str) and val.lower() in ("extreme", "elevated", "high"):
            score += 12
            drivers.append(f"{key}={val}")
    if "Funding Extreme" in tags or "Elevated Open Interest" in tags:
        score += 15
        drivers.append("Funding/OI leverage pressure tags")
    label = LeverageEnvironment.NORMAL.value
    if score >= 80:
        label = LeverageEnvironment.EXTREME.value
    elif score >= 55:
        label = LeverageEnvironment.ELEVATED.value
    elif score <= 25:
        label = LeverageEnvironment.CONSERVATIVE.value
    if crowded and label == LeverageEnvironment.NORMAL.value:
        label = LeverageEnvironment.ELEVATED.value
    return CategoryScore("leverage", _clamp(score), label, drivers or ["No elevated leverage flags"])


def score_event_risk(*, macro_event: bool = False, near_options_expiry: bool = False, intelligence: dict[str, Any] | None = None) -> CategoryScore:
    intel = intelligence or {}
    score = 15.0
    drivers = []
    if macro_event or intel.get("macro_event"):
        score += 35
        drivers.append("Major macro event window")
    if near_options_expiry:
        score += 20
        drivers.append("Options expiry / gamma window")
    if intel.get("macro_bias") in ("Cautious", "Risk-Off", "Uncertain"):
        score += 10
        drivers.append(f"Macro bias={intel.get('macro_bias')}")
    if score >= 55:
        label = EventRisk.HIGH.value
    elif score >= 30:
        label = EventRisk.ELEVATED.value
    else:
        label = EventRisk.LOW.value
    return CategoryScore("event", _clamp(score), label, drivers or ["No scheduled high-impact event flags"])


def score_data_risk(*, decision: dict[str, Any], analysis: dict[str, Any], feature_dq: float | None = None) -> CategoryScore:
    dqs = float(decision.get("data_quality_score") or analysis.get("data_quality") or 80)
    # Invert: low DQS → high data risk
    score = _clamp(100.0 - dqs)
    drivers = [f"DQS={dqs:.0f}"]
    if feature_dq is not None and feature_dq < 0.6:
        score = _clamp(score + 15)
        drivers.append(f"Feature data quality={feature_dq:.2f}")
    missing_layers = 8 - len(analysis.get("layer_results") or [])
    if missing_layers > 0:
        score = _clamp(score + missing_layers * 5)
        drivers.append(f"Missing layers={missing_layers}")
    label = "Degraded" if score >= 50 else ("Watch" if score >= 30 else "Good")
    return CategoryScore("data", score, label, drivers)


def score_execution_risk(*, liquidity: CategoryScore, volatility: CategoryScore, event: CategoryScore) -> CategoryScore:
    score = 0.45 * liquidity.score + 0.35 * volatility.score + 0.20 * event.score
    drivers = ["Derived from liquidity + volatility + event"]
    if liquidity.label in (LiquidityState.THIN.value, LiquidityState.CRITICAL.value):
        drivers.append("Thin/critical liquidity raises slippage risk")
    label = "Elevated" if score >= 55 else ("Moderate" if score >= 35 else "Contained")
    return CategoryScore("execution", _clamp(score), label, drivers)


def score_stop_noise(*, volatility: CategoryScore, liquidity: CategoryScore, analysis: dict[str, Any]) -> CategoryScore:
    tags = {t for r in (analysis.get("layer_results") or []) for t in (r.get("tags") or [])}
    score = 0.6 * volatility.score + 0.4 * liquidity.score
    drivers = []
    if "Sweep Probability" in tags:
        score += 12
        drivers.append("Recent / nearby sweep frequency")
    if score >= 70:
        label = StopNoise.HIGH_STOP_OUT.value
    elif score >= 45:
        label = StopNoise.INCREASED_NOISE.value
    else:
        label = StopNoise.STABLE.value
    return CategoryScore("stop_noise", _clamp(score), label, drivers or ["ATR/volatility noise assessment"])
