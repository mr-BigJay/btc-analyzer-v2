"""Layer 1 — Spot Market (Ch.6 §6.4)."""

from __future__ import annotations

from src.analysis.contracts import SignalBias
from src.analysis.context import MarketContext
from src.analysis.indicators import last, sma
from src.analysis.layers.base import BaseLayer


class SpotLayer(BaseLayer):
    NAME = "Spot"

    def analyze(self, ctx: MarketContext) -> LayerResult:
        quality = 0.3
        tags: list[str] = []
        details: dict = {}
        score = 0.0

        price = ctx.spot_price or ctx.mark_price
        closes = ctx.closes
        vols = ctx.volumes

        if closes and len(closes) >= 20:
            quality = 0.8
            vwap_proxy = sum(closes[-20:]) / 20
            details["vwap_proxy"] = vwap_proxy
            if price:
                dist = (price - vwap_proxy) / vwap_proxy
                details["price_vs_vwap"] = dist
                score += max(-1.0, min(1.0, dist * 8))
                if dist > 0.005:
                    tags.append("Buyer Dominance")
                elif dist < -0.005:
                    tags.append("Seller Dominance")

            vol_sma = last(sma(vols, 20)) if vols else None
            cur_vol = vols[-1] if vols else None
            details["volume"] = cur_vol
            details["volume_sma20"] = vol_sma
            if cur_vol and vol_sma and vol_sma > 0:
                quality = min(1.0, quality + 0.1)
                if cur_vol > vol_sma * 1.4 and score > 0:
                    tags.append("Accumulation")
                    score += 0.15
                elif cur_vol > vol_sma * 1.4 and score < 0:
                    tags.append("Distribution")
                    score -= 0.15

        # Order book imbalance as spot proxy
        bids = (ctx.order_book or {}).get("bids") or []
        asks = (ctx.order_book or {}).get("asks") or []
        if bids and asks:
            quality = max(quality, 0.6)
            try:
                bid_sz = sum(float(b[1]) for b in bids[:10] if isinstance(b, (list, tuple)) and len(b) > 1)
                ask_sz = sum(float(a[1]) for a in asks[:10] if isinstance(a, (list, tuple)) and len(a) > 1)
                imb = (bid_sz - ask_sz) / (bid_sz + ask_sz) if (bid_sz + ask_sz) else 0.0
                details["orderbook_imbalance"] = imb
                score += max(-0.4, min(0.4, imb))
                if imb > 0.15:
                    tags.append("Spot Strength")
                elif imb < -0.15:
                    tags.append("Seller Dominance")
            except (TypeError, ValueError, IndexError):
                pass

        if quality < 0.4:
            return self._result(
                SignalBias.NEUTRAL.value,
                35,
                "Insufficient spot evidence — neutral default.",
                timeframe=ctx.timeframe,
                details=details,
                tags=tags or ["Low Data Quality"],
                data_quality=quality,
            )

        signal = self._clamp_signal_from_score(score)
        conf = 50 + abs(score) * 45
        summary = f"Spot score={score:.2f}; tags={', '.join(tags) or 'none'}."
        return self._result(signal, conf, summary, timeframe=ctx.timeframe, details=details, tags=tags, data_quality=quality)
