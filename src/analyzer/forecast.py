"""۴-hour directional forecast with calibrated confidence and coherent targets."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.analyzer.models import OverviewAnalysis, Trend
from src.db.models import TakerVolume
from src.options.pipeline import OptionsPipeline

logger = logging.getLogger(__name__)

MAX_CONFIDENCE = 88.0
MIN_CONFIDENCE = 35.0


@dataclass
class Forecast4h:
    price: float
    direction: str
    direction_label: str
    direction_score: float
    confidence: float
    support: float | None
    resistance: float | None
    primary_target: float | None
    invalidation: float | None
    put_wall: float | None
    call_wall: float | None
    gamma_regime: str
    gamma_regime_label: str
    cvd_signal: str
    options_flow: str
    whale_signal: str
    bullish_reasons: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    summary: str = ""


class ForecastEngine:
    def build(self, session: Session, analysis: OverviewAnalysis) -> Forecast4h:
        tf4h = analysis.timeframes["4h"]
        lv = tf4h.levels or {}
        support = lv.get("support")
        resistance = lv.get("resistance")
        price = analysis.price

        opts = self._options_context(session, price)
        cvd = self._cvd_context(session)

        components: list[tuple[float, float, str]] = []

        tech = (tf4h.score - 50) * 2
        components.append((tech, 0.30, "tech_4h"))

        mom = self._momentum_score(tf4h)
        components.append((mom, 0.12, "momentum"))

        deriv = self._derivatives_score(analysis, cvd)
        components.append((deriv, 0.18, "derivatives"))

        liq = self._liquidation_score(analysis, price)
        components.append((liq, 0.12, "liquidations"))

        opt_score = opts.get("flow_score", 0)
        components.append((opt_score, 0.10, "options"))

        macro_onchain = self._macro_onchain_score(analysis)
        components.append((macro_onchain, 0.06, "macro"))

        coinex_score = self._coinex_score(analysis)
        components.append((coinex_score, 0.08, "coinex"))

        coinex_ai_score = self._coinex_ai_score(analysis)
        components.append((coinex_ai_score, 0.10, "coinex_ai"))

        direction_score = sum(s * w for s, w, _ in components)
        direction_score = max(-100, min(100, direction_score))

        if direction_score > 12:
            direction = "bullish"
            direction_label = "صعودی"
        elif direction_score < -12:
            direction = "bearish"
            direction_label = "نزولی"
        else:
            direction = "neutral"
            direction_label = "خنثی / رنج"

        primary_target, invalidation = self._targets(
            direction, price, support, resistance, analysis
        )

        bullish, risks = self._reasons(
            analysis, tf4h, opts, cvd, direction, price, support, resistance
        )

        confidence = self._confidence(
            direction_score, direction, components, analysis, tf4h, primary_target, price
        )

        summary = self._summary(
            direction,
            direction_label,
            confidence,
            price,
            support,
            resistance,
            primary_target,
            invalidation,
            risks,
        )

        return Forecast4h(
            price=price,
            direction=direction,
            direction_label=direction_label,
            direction_score=round(direction_score, 1),
            confidence=round(confidence, 1),
            support=support,
            resistance=resistance,
            primary_target=primary_target,
            invalidation=invalidation,
            put_wall=opts.get("put_wall"),
            call_wall=opts.get("call_wall"),
            gamma_regime=opts.get("gamma_regime", "neutral"),
            gamma_regime_label=opts.get("gamma_regime_label", "خنثی"),
            cvd_signal=cvd.get("label", "نامشخص"),
            options_flow=opts.get("flow_label", "خنثی"),
            whale_signal=opts.get("whale_label", "خنثی"),
            bullish_reasons=bullish,
            risks=risks,
            summary=summary,
        )

    def _momentum_score(self, tf4h) -> float:
        ind = tf4h.indicators or {}
        score = 0.0
        rsi = ind.get("rsi")
        if rsi is not None:
            score += (rsi - 50) * 1.2
        macd_h = ind.get("macd_hist")
        if macd_h is not None:
            score += 25 if macd_h > 0 else -25
        stoch = ind.get("stoch_signal")
        if stoch == "oversold":
            score += 15
        elif stoch == "overbought":
            score -= 15
        return max(-100, min(100, score))

    def _derivatives_score(self, analysis: OverviewAnalysis, cvd: dict) -> float:
        d = analysis.derivatives
        score = cvd.get("score", 0)
        if d.funding_rate is not None:
            score -= d.funding_rate * 10000
        if d.long_short_ratio is not None:
            score += (d.long_short_ratio - 1) * 30
        if d.taker_signal == "buyers_dominant":
            score += 20
        elif d.taker_signal == "sellers_dominant":
            score -= 20
        return max(-100, min(100, score))

    def _liquidation_score(self, analysis: OverviewAnalysis, price: float) -> float:
        liq = analysis.liquidations
        if not liq:
            return 0.0
        score = 0.0
        if liq.signal == "liq_cluster_above":
            score += 18
        elif liq.signal == "liq_cluster_below":
            score -= 18
        below = liq.zones_below or []
        above = liq.zones_above or []
        if below and above:
            below_usd = sum(z.get("total_usd", 0) for z in below)
            above_usd = sum(z.get("total_usd", 0) for z in above)
            if below_usd > above_usd * 1.3:
                score -= 12
            elif above_usd > below_usd * 1.3:
                score += 12
        nearest = liq.nearest_zone
        if nearest and nearest.get("price"):
            if nearest["price"] < price and nearest.get("long_usd", 0) > nearest.get("short_usd", 0):
                score -= 10
            elif nearest["price"] > price and nearest.get("short_usd", 0) > nearest.get("long_usd", 0):
                score += 10
        return max(-100, min(100, score))

    def _coinex_score(self, analysis: OverviewAnalysis) -> float:
        cx = analysis.coinex
        if not cx:
            return 0.0
        score = 0.0
        if cx.premium_pct is not None:
            score += max(-30, min(30, cx.premium_pct * 400))
        if cx.funding_rate is not None:
            score -= cx.funding_rate * 8000
        if cx.taker_buy_sell_ratio is not None:
            score += (cx.taker_buy_sell_ratio - 1) * 80
        if cx.oi_change_pct is not None:
            score += max(-20, min(20, cx.oi_change_pct * 3))
        if cx.signal == "bullish":
            score += 10
        elif cx.signal == "bearish":
            score -= 10
        return max(-100, min(100, score))

    def _coinex_ai_score(self, analysis: OverviewAnalysis) -> float:
        ai = analysis.coinex_ai
        if not ai:
            return 0.0
        score = 0.0
        if ai.short_orientation == "up":
            score += 20
        elif ai.short_orientation == "down":
            score -= 20
        if ai.long_orientation == "up":
            score += 25
        elif ai.long_orientation == "down":
            score -= 25
        if ai.signal == "bullish":
            score += 12
        elif ai.signal == "bearish":
            score -= 12
        return max(-100, min(100, score))

    def _macro_onchain_score(self, analysis: OverviewAnalysis) -> float:
        score = 0.0
        if analysis.macro:
            if analysis.macro.macro_bias == "bullish_crypto":
                score += 25
            elif analysis.macro.macro_bias == "bearish_crypto":
                score -= 25
        if analysis.onchain:
            if analysis.onchain.mvrv_signal == "undervalued":
                score += 15
            elif analysis.onchain.mvrv_signal in ("overvalued", "elevated"):
                score -= 15
        if analysis.sentiment.signal == "extreme_fear":
            score += 10
        elif analysis.sentiment.signal == "extreme_greed":
            score -= 10
        return max(-100, min(100, score))

    def _cvd_context(self, session: Session) -> dict:
        rows = session.execute(
            select(TakerVolume).order_by(desc(TakerVolume.timestamp)).limit(24)
        ).scalars().all()
        if not rows:
            return {"score": 0, "label": "داده CVD موجود نیست"}

        buy = sum(r.buy_volume for r in rows)
        sell = sum(r.sell_volume for r in rows)
        total = buy + sell
        if total <= 0:
            return {"score": 0, "label": "CVD خنثی"}

        delta_pct = (buy - sell) / total * 100
        if delta_pct > 8:
            return {"score": 35, "label": f"CVD مثبت ۲۴ساعته (+{delta_pct:.1f}%)"}
        if delta_pct < -8:
            return {"score": -35, "label": f"CVD منفی ۲۴ساعته ({delta_pct:.1f}%)"}
        return {"score": delta_pct * 2, "label": f"CVD تقریباً خنثی ({delta_pct:+.1f}%)"}

    def _options_context(self, session: Session, price: float) -> dict:
        data = OptionsPipeline.get_latest(session)
        if not data:
            return {
                "flow_score": 0,
                "flow_label": "بدون داده آپشن",
                "gamma_regime": "neutral",
                "gamma_regime_label": "نامشخص",
                "put_wall": None,
                "call_wall": None,
                "whale_label": "نامشخص",
            }

        screener = data.get("screener", {})
        rows = screener.get("rows", [])
        risk = data.get("risk_profile", {})
        points = risk.get("points", [])

        call_premium = 0.0
        put_premium = 0.0
        call_strikes: dict[float, float] = {}
        put_strikes: dict[float, float] = {}
        whale_bull = 0
        whale_bear = 0

        for r in rows:
            val = float(r.get("entry_value_usd", 0))
            strike = float(r.get("strike", 0))
            opt = r.get("option_type", "")
            side = r.get("side", "long")
            sign = 1 if side == "long" else -1

            if opt == "call":
                call_premium += val * sign
                call_strikes[strike] = call_strikes.get(strike, 0) + val
                if val > 500_000 and side == "long":
                    whale_bull += 1
                elif val > 500_000 and side == "short":
                    whale_bear += 1
            elif opt == "put":
                put_premium += val * sign
                put_strikes[strike] = put_strikes.get(strike, 0) + val
                if val > 500_000 and side == "long":
                    whale_bear += 1
                elif val > 500_000 and side == "short":
                    whale_bull += 1

        flow_score = 0.0
        if call_premium + put_premium != 0:
            flow_score = (call_premium - put_premium) / max(abs(call_premium) + abs(put_premium), 1) * 60

        if flow_score > 15:
            flow_label = "جریان آپشن صعودی"
        elif flow_score < -15:
            flow_label = "جریان آپشن نزولی"
        else:
            flow_label = "جریان آپشن خنثی"

        put_below = [s for s in put_strikes if s < price]
        call_above = [s for s in call_strikes if s > price]
        put_wall = max(put_below, key=lambda s: put_strikes[s]) if put_below else None
        call_wall = max(call_above, key=lambda s: call_strikes[s]) if call_above else None

        gamma_regime = "neutral"
        gamma_label = "گامای خنثی"
        if points:
            nearest = min(points, key=lambda p: abs(p.get("spot", 0) - price))
            gamma = nearest.get("gamma", 0)
            if gamma < -0.0001:
                gamma_regime = "short_gamma"
                gamma_label = "Short Gamma — نوسان بالا"
            elif gamma > 0.0001:
                gamma_regime = "long_gamma"
                gamma_label = "Long Gamma — تثبیل نوسان"

        if whale_bull > whale_bear:
            whale_label = "فعالیت نهنگ صعودی"
        elif whale_bear > whale_bull:
            whale_label = "فعالیت نهنگ نزولی"
        else:
            whale_label = "فعالیت نهنگ خنثی"

        return {
            "flow_score": flow_score,
            "flow_label": flow_label,
            "gamma_regime": gamma_regime,
            "gamma_regime_label": gamma_label,
            "put_wall": put_wall,
            "call_wall": call_wall,
            "whale_label": whale_label,
        }

    def _targets(
        self,
        direction: str,
        price: float,
        support: float | None,
        resistance: float | None,
        analysis: OverviewAnalysis,
    ) -> tuple[float | None, float | None]:
        liq = analysis.liquidations

        if direction == "bearish":
            target = support
            if liq and liq.zones_below:
                heavy = max(liq.zones_below, key=lambda z: z.get("total_usd", 0))
                if heavy.get("price"):
                    target = heavy["price"] if not target else min(target, heavy["price"])
            invalidation = resistance
            if target and target >= price:
                target = price * 0.985
            return (round(target, 0) if target else None, round(invalidation, 0) if invalidation else None)

        if direction == "bullish":
            target = resistance
            if liq and liq.zones_above:
                heavy = max(liq.zones_above, key=lambda z: z.get("total_usd", 0))
                if heavy.get("price"):
                    target = heavy["price"] if not target else max(target, heavy["price"])
            invalidation = support
            if target and target <= price:
                target = price * 1.015
            return (round(target, 0) if target else None, round(invalidation, 0) if invalidation else None)

        mid = None
        if support and resistance:
            mid = (support + resistance) / 2
        return (round(mid, 0) if mid else None, None)

    def _confidence(
        self,
        direction_score: float,
        direction: str,
        components: list,
        analysis: OverviewAnalysis,
        tf4h,
        primary_target: float | None,
        price: float,
    ) -> float:
        base = 38 + abs(direction_score) * 0.42
        base = min(78, base)

        aligned_layers = sum(
            1
            for layer in tf4h.layers
            if (direction == "bullish" and layer.score > 52)
            or (direction == "bearish" and layer.score < 48)
        )
        base += aligned_layers * 2.5

        contradictions = 0
        if direction == "bearish" and tf4h.trend == Trend.BULLISH:
            contradictions += 1
        if direction == "bullish" and tf4h.trend == Trend.BEARISH:
            contradictions += 1
        if primary_target and direction == "bearish" and primary_target > price:
            contradictions += 2
        if primary_target and direction == "bullish" and primary_target < price:
            contradictions += 2
        if analysis.mtf_aligned and direction == "bearish":
            wk = analysis.timeframes["1w"].trend
            if wk == Trend.BULLISH:
                contradictions += 1
        if analysis.mtf_aligned and direction == "bullish":
            wk = analysis.timeframes["1w"].trend
            if wk == Trend.BEARISH:
                contradictions += 1

        spread = max(abs(s) for s, _, _ in components) - min(abs(s) for s, _, _ in components)
        if spread > 60:
            contradictions += 1

        base -= contradictions * 9
        base = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, base))
        return base

    def _reasons(
        self,
        analysis: OverviewAnalysis,
        tf4h,
        opts: dict,
        cvd: dict,
        direction: str,
        price: float,
        support: float | None,
        resistance: float | None,
    ) -> tuple[list[str], list[str]]:
        bullish: list[str] = []
        risks: list[str] = []

        ind = tf4h.indicators or {}
        if tf4h.trend == Trend.BULLISH:
            bullish.append("روند 4h صعودی")
        elif tf4h.trend == Trend.BEARISH:
            risks.append("روند 4h نزولی")

        if ind.get("rsi") and ind["rsi"] < 35:
            bullish.append(f"RSI اشباع فروش ({ind['rsi']:.0f})")
        elif ind.get("rsi") and ind["rsi"] > 65:
            risks.append(f"RSI اشباع خرید ({ind['rsi']:.0f})")

        smc = (tf4h.levels or {}).get("smc_signal", "")
        if smc in ("bos_bullish", "choch_bullish"):
            bullish.append("شکست ساختاری صعودی (SMC)")
        elif smc in ("bos_bearish", "choch_bearish"):
            risks.append("شکست ساختاری نزولی (SMC)")

        d = analysis.derivatives
        if d.taker_signal == "buyers_dominant":
            bullish.append("تیکر خرید غالب")
        elif d.taker_signal == "sellers_dominant":
            risks.append("تیکر فروش غالب")

        if cvd.get("score", 0) > 10:
            bullish.append(cvd.get("label", "CVD مثبت"))
        elif cvd.get("score", 0) < -10:
            risks.append(cvd.get("label", "CVD منفی"))

        put_wall = opts.get("put_wall")
        call_wall = opts.get("call_wall")
        if put_wall and price < put_wall:
            risks.append(f"قیمت زیر Put Wall (${put_wall:,.0f})")
        elif put_wall and price > put_wall:
            bullish.append(f"حمایت Put Wall (${put_wall:,.0f})")

        if opts.get("gamma_regime") == "short_gamma":
            risks.append(opts.get("gamma_regime_label", "Short Gamma"))

        if opts.get("flow_score", 0) > 15:
            bullish.append(opts.get("flow_label", "جریان آپشن صعودی"))
        elif opts.get("flow_score", 0) < -15:
            risks.append(opts.get("flow_label", "جریان آپشن نزولی"))

        if opts.get("whale_label", "").endswith("صعودی"):
            bullish.append(opts.get("whale_label"))
        elif opts.get("whale_label", "").endswith("نزولی"):
            risks.append(opts.get("whale_label"))

        liq = analysis.liquidations
        if liq and liq.zones_below:
            long_heavy = sum(
                1 for z in liq.zones_below if z.get("long_usd", 0) > z.get("short_usd", 0)
            )
            if long_heavy >= 2:
                risks.append("لیکوئیدیشن لانگ غالب — فشار نزولی")

        if analysis.macro and analysis.macro.macro_bias == "bearish_crypto":
            risks.append("ماکرو: فشار دلار / ریسک‌گریز")
        elif analysis.macro and analysis.macro.macro_bias == "bullish_crypto":
            bullish.append("ماکرو: محیط ریسک‌پذیر")

        if analysis.coinex:
            cx = analysis.coinex
            if cx.signal == "bullish":
                bullish.append(f"CoinEx Futures: {cx.research_note}")
            elif cx.signal == "bearish":
                risks.append(f"CoinEx Futures: {cx.research_note}")
            elif cx.research_note and "بدون سیگنال" not in cx.research_note:
                bullish.append(f"CoinEx: {cx.research_note}")

        if analysis.coinex_ai:
            ai = analysis.coinex_ai
            if ai.signal == "bullish":
                bullish.append(f"CoinEx AI Research: {ai.summary}")
            elif ai.signal == "bearish":
                risks.append(f"CoinEx AI Research: {ai.summary}")
            elif ai.summary:
                bullish.append(f"CoinEx AI Research: {ai.summary}")

        if support and price < support * 1.01:
            bullish.append(f"نزدیک حمایت ${support:,.0f}")
        if resistance and price > resistance * 0.99:
            risks.append(f"زیر مقاومت سنگین ${resistance:,.0f}")

        if not bullish:
            bullish.append("سیگنال صعودی قوی ثبت نشده")
        if not risks:
            risks.append("ریسک مشخصی شناسایی نشد")

        return bullish[:6], risks[:8]

    def _summary(
        self,
        direction: str,
        direction_label: str,
        confidence: float,
        price: float,
        support: float | None,
        resistance: float | None,
        primary_target: float | None,
        invalidation: float | None,
        risks: list[str],
    ) -> str:
        if direction == "bearish":
            parts = [
                f"مدل برای ۴ ساعت آینده تمایل {direction_label} می‌بیند (اعتماد {confidence:.0f}٪)."
            ]
            if primary_target and primary_target < price:
                parts.append(f"هدف محتمل نزولی نزدیک ${primary_target:,.0f} است.")
            elif support:
                parts.append(f"در صورت فشار فروش، حمایت ${support:,.0f} محتمل‌ترین مقصد است.")
            if resistance:
                parts.append(
                    f"شکست و تثبیت بالای ${resistance:,.0f} می‌تواند سناریوی نزولی را باطل کند."
                )
            return " ".join(parts)

        if direction == "bullish":
            parts = [
                f"مدل برای ۴ ساعت آینده تمایل {direction_label} می‌بیند (اعتماد {confidence:.0f}٪)."
            ]
            if primary_target and primary_target > price:
                parts.append(f"هدف محتمل صعودی نزدیک ${primary_target:,.0f} است.")
            elif resistance:
                parts.append(f"مقاومت ${resistance:,.0f} سطح کلیدی برای ادامه رشد است.")
            if support:
                parts.append(f"از دست رفتن ${support:,.0f} سناریوی صعودی را تضعیف می‌کند.")
            return " ".join(parts)

        return (
            f"بازار در ۴ ساعت آینده احتمالاً در رنج می‌ماند (اعتماد {confidence:.0f}٪). "
            f"معامله در محدوده ${support:,.0f} تا ${resistance:,.0f} محتمل است."
            if support and resistance
            else f"سیگنال جهت‌دار قوی نیست — اعتماد {confidence:.0f}٪."
        )


def forecast_to_dict(f: Forecast4h) -> dict:
    return {
        "price": f.price,
        "direction": f.direction,
        "direction_label": f.direction_label,
        "direction_score": f.direction_score,
        "confidence": f.confidence,
        "support": f.support,
        "resistance": f.resistance,
        "primary_target": f.primary_target,
        "invalidation": f.invalidation,
        "put_wall": f.put_wall,
        "call_wall": f.call_wall,
        "gamma_regime": f.gamma_regime,
        "gamma_regime_label": f.gamma_regime_label,
        "cvd_signal": f.cvd_signal,
        "options_flow": f.options_flow,
        "whale_signal": f.whale_signal,
        "bullish_reasons": f.bullish_reasons,
        "risks": f.risks,
        "summary": f.summary,
    }
