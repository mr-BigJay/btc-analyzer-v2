import logging
from datetime import datetime, timezone

import pandas as pd
import pandas_ta as ta
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.analyzer.indicators import (
    add_bollinger,
    add_stochastic,
    bollinger_signal,
    fibonacci_levels,
    find_support_resistance,
    stochastic_signal,
)
from src.analyzer.smc import analyze_smc
from src.analyzer.models import (
    CoinExContext,
    DerivativesContext,
    LayerScore,
    LiquidationContext,
    MarketRegime,
    OnChainContext,
    OverviewAnalysis,
    SentimentContext,
    MacroContext,
    TimeframeAnalysis,
    Trend,
)
from src.config import settings
from src.db.models import (
    CoinExFuturesSnapshot,
    FearGreedIndex,
    FundingRate,
    LongShortRatio,
    OHLCVCandle,
    OnChainMetric,
    OpenInterest,
    MacroMetric,
    LiquidationLevel,
    TakerVolume,
    TickerSnapshot,
)

logger = logging.getLogger(__name__)

LAYER_WEIGHTS = {
    "trend": 0.35,
    "momentum": 0.25,
    "volume": 0.20,
    "volatility": 0.10,
    "structure": 0.10,
}


class TechnicalAnalyzer:
    def analyze_dataframe(self, df: pd.DataFrame, timeframe: str) -> TimeframeAnalysis:
        df = df.copy()
        df["ema20"] = ta.ema(df["close"], length=20)
        df["ema50"] = ta.ema(df["close"], length=50)
        df["ema200"] = ta.ema(df["close"], length=200)
        df["rsi"] = ta.rsi(df["close"], length=14)
        macd = ta.macd(df["close"])
        if macd is not None:
            df = pd.concat([df, macd], axis=1)
        df["adx"] = ta.adx(df["high"], df["low"], df["close"], length=14).iloc[:, 0]
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        df["vol_ma20"] = df["volume"].rolling(20).mean()
        df["obv"] = ta.obv(df["close"], df["volume"])
        df = add_bollinger(df)
        df = add_stochastic(df)

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        price = float(latest["close"])

        bb = bollinger_signal(latest, df)
        stoch = stochastic_signal(latest, prev, df)
        sr = find_support_resistance(df)
        fib = fibonacci_levels(df)
        smc = analyze_smc(df, price)

        trend_layer = self._score_trend(latest, prev)
        momentum_layer = self._score_momentum(latest, prev, df, stoch)
        volume_layer = self._score_volume(latest, df)
        volatility_layer = self._score_volatility(latest, df, bb)
        structure_layer, structure_label = self._score_structure(df, sr, fib, smc)

        layers = [trend_layer, momentum_layer, volume_layer, volatility_layer, structure_layer]
        score = sum(layer.score * layer.weight for layer in layers)
        trend = self._score_to_trend(score)
        regime = self._detect_regime(latest, df)
        confidence = self._calc_confidence(layers, trend)

        macd_col = [c for c in df.columns if c.startswith("MACD_") and not c.startswith("MACDs_") and not c.startswith("MACDh_")]
        macdh_col = [c for c in df.columns if c.startswith("MACDh_")]

        indicators = {
            "ema20": self._safe_float(latest.get("ema20")),
            "ema50": self._safe_float(latest.get("ema50")),
            "ema200": self._safe_float(latest.get("ema200")),
            "rsi": self._safe_float(latest.get("rsi")),
            "macd": self._safe_float(latest[macd_col[0]]) if macd_col else None,
            "macd_hist": self._safe_float(latest[macdh_col[0]]) if macdh_col else None,
            "adx": self._safe_float(latest.get("adx")),
            "atr": self._safe_float(latest.get("atr")),
            "volume_ratio": self._safe_float(
                latest["volume"] / latest["vol_ma20"]
                if latest.get("vol_ma20") and latest["vol_ma20"] > 0
                else None
            ),
            "bb_pct_b": bb.get("pct_b"),
            "bb_signal": bb.get("signal"),
            "stoch_k": stoch.get("stoch_k"),
            "stoch_d": stoch.get("stoch_d"),
            "stoch_signal": stoch.get("signal"),
        }

        levels = {
            "support": sr.get("support"),
            "resistance": sr.get("resistance"),
            "sr_signal": sr.get("signal"),
            "fibonacci": fib.get("levels"),
            "fib_nearest": fib.get("nearest_level"),
            "fib_signal": fib.get("signal"),
            "smc_signal": smc.get("signal"),
            "active_fvg": smc.get("active_fvg"),
            "nearest_ob": smc.get("nearest_ob"),
            "bos_choch": smc.get("bos_choch"),
        }

        return TimeframeAnalysis(
            timeframe=timeframe,
            trend=trend,
            score=round(score, 1),
            confidence=round(confidence, 1),
            regime=regime,
            price=price,
            layers=layers,
            indicators=indicators,
            structure=structure_label,
            levels=levels,
        )

    def _score_trend(self, latest: pd.Series, prev: pd.Series) -> LayerScore:
        score = 50.0
        details: dict = {}

        price = latest["close"]
        ema20 = latest.get("ema20")
        ema50 = latest.get("ema50")
        ema200 = latest.get("ema200")

        if pd.notna(ema50) and pd.notna(ema200):
            if price > ema50 > ema200:
                score += 25
                details["ema_alignment"] = "bullish"
            elif price < ema50 < ema200:
                score -= 25
                details["ema_alignment"] = "bearish"
            else:
                details["ema_alignment"] = "mixed"

        if pd.notna(ema20) and pd.notna(prev.get("ema20")):
            if latest["ema20"] > prev["ema20"]:
                score += 10
            else:
                score -= 10

        if pd.notna(ema50) and price > ema50:
            score += 10
        elif pd.notna(ema50):
            score -= 10

        return LayerScore("trend", max(0, min(100, score)), LAYER_WEIGHTS["trend"], details)

    def _score_momentum(self, latest: pd.Series, prev: pd.Series, df: pd.DataFrame, stoch: dict) -> LayerScore:
        score = 50.0
        details: dict = {}
        rsi = latest.get("rsi")

        if pd.notna(rsi):
            if rsi > 60:
                score += min(20, (rsi - 60))
                details["rsi"] = "bullish"
            elif rsi < 40:
                score -= min(20, (40 - rsi))
                details["rsi"] = "bearish"
            else:
                details["rsi"] = "neutral"

        macdh_cols = [c for c in df.columns if c.startswith("MACDh_")]
        if macdh_cols:
            hist = latest[macdh_cols[0]]
            prev_hist = prev[macdh_cols[0]]
            if pd.notna(hist):
                if hist > 0:
                    score += 15
                    details["macd"] = "positive"
                else:
                    score -= 15
                    details["macd"] = "negative"
                if pd.notna(prev_hist) and hist > prev_hist:
                    score += 5

        score += stoch.get("score_delta", 0)
        if stoch.get("signal"):
            details["stochastic"] = stoch["signal"]
        if stoch.get("crossover"):
            details["stoch_crossover"] = stoch["crossover"]

        return LayerScore("momentum", max(0, min(100, score)), LAYER_WEIGHTS["momentum"], details)

    def _score_volume(self, latest: pd.Series, df: pd.DataFrame) -> LayerScore:
        score = 50.0
        details: dict = {}
        vol_ma = latest.get("vol_ma20")

        if pd.notna(vol_ma) and vol_ma > 0:
            ratio = latest["volume"] / vol_ma
            details["volume_ratio"] = round(float(ratio), 2)
            price_change = latest["close"] - df.iloc[-2]["close"]

            if ratio > 1.2:
                if price_change > 0:
                    score += 20
                    details["volume"] = "bullish_confirmation"
                else:
                    score -= 20
                    details["volume"] = "bearish_confirmation"
            elif ratio < 0.8:
                score -= 5
                details["volume"] = "low"

        if "obv" in df.columns and len(df) > 5:
            obv_slope = df["obv"].iloc[-1] - df["obv"].iloc[-5]
            if obv_slope > 0:
                score += 10
                details["obv"] = "rising"
            else:
                score -= 10
                details["obv"] = "falling"

        return LayerScore("volume", max(0, min(100, score)), LAYER_WEIGHTS["volume"], details)

    def _score_volatility(self, latest: pd.Series, df: pd.DataFrame, bb: dict) -> LayerScore:
        score = 50.0
        details: dict = {}
        atr = latest.get("atr")
        price = latest["close"]

        if pd.notna(atr) and price > 0:
            atr_pct = atr / price * 100
            details["atr_pct"] = round(float(atr_pct), 2)
            if atr_pct > 5:
                score -= 15
                details["regime_hint"] = "high_volatility"
            elif atr_pct < 2:
                score += 5
                details["regime_hint"] = "low_volatility"

        score += bb.get("score_delta", 0) * 0.5
        if bb.get("signal"):
            details["bollinger"] = bb["signal"]

        return LayerScore("volatility", max(0, min(100, score)), LAYER_WEIGHTS["volatility"], details)

    def _score_structure(self, df: pd.DataFrame, sr: dict, fib: dict, smc: dict) -> tuple[LayerScore, str]:
        score = 50.0
        lookback = min(20, len(df) - 1)
        if lookback < 5:
            return LayerScore("structure", 50.0, LAYER_WEIGHTS["structure"]), "insufficient_data"

        recent = df.tail(lookback)
        highs = recent["high"].values
        lows = recent["low"].values

        hh = highs[-1] > highs[len(highs) // 2]
        hl = lows[-1] > lows[len(lows) // 2]
        lh = highs[-1] < highs[len(highs) // 2]
        ll = lows[-1] < lows[len(lows) // 2]

        if hh and hl:
            score = 75
            label = "higher_highs_higher_lows"
        elif lh and ll:
            score = 25
            label = "lower_highs_lower_lows"
        else:
            score = 50
            label = "mixed_structure"

        score += sr.get("score_delta", 0)
        score += fib.get("score_delta", 0)
        score += smc.get("score_delta", 0)
        score = max(0, min(100, score))

        details = {
            "pattern": label,
            "sr_signal": sr.get("signal"),
            "fib_signal": fib.get("signal"),
            "smc_signal": smc.get("signal"),
            "support": sr.get("support"),
            "resistance": sr.get("resistance"),
        }

        return LayerScore("structure", score, LAYER_WEIGHTS["structure"], details), label

    def _detect_regime(self, latest: pd.Series, df: pd.DataFrame) -> MarketRegime:
        adx = latest.get("adx")
        atr = latest.get("atr")
        price = latest["close"]

        if pd.notna(atr) and price > 0 and (atr / price * 100) > 5:
            return MarketRegime.VOLATILE
        if pd.notna(adx) and adx < 25:
            return MarketRegime.RANGING
        return MarketRegime.TRENDING

    def _calc_confidence(self, layers: list[LayerScore], trend: Trend) -> float:
        bullish_layers = sum(1 for l in layers if l.score > 55)
        bearish_layers = sum(1 for l in layers if l.score < 45)
        aligned = bullish_layers if trend == Trend.BULLISH else bearish_layers if trend == Trend.BEARISH else 0
        base = 40 + aligned * 12
        spread = max(l.score for l in layers) - min(l.score for l in layers)
        if spread < 20:
            base += 10
        return min(95, max(30, base))

    @staticmethod
    def _score_to_trend(score: float) -> Trend:
        if score >= 60:
            return Trend.BULLISH
        if score <= 40:
            return Trend.BEARISH
        return Trend.NEUTRAL

    @staticmethod
    def _safe_float(val) -> float | None:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        return round(float(val), 4)


class AnalysisService:
    def __init__(self) -> None:
        self.technical = TechnicalAnalyzer()

    def _load_candles(self, session: Session, timeframe: str) -> pd.DataFrame:
        stmt = (
            select(OHLCVCandle)
            .where(
                OHLCVCandle.symbol == settings.symbol,
                OHLCVCandle.timeframe == timeframe,
            )
            .order_by(OHLCVCandle.open_time)
        )
        rows = session.execute(stmt).scalars().all()
        if not rows:
            raise ValueError(f"No candle data for timeframe {timeframe}")

        return pd.DataFrame(
            [
                {
                    "open_time": r.open_time,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                }
                for r in rows
            ]
        )

    def _derivatives_context(self, session: Session) -> DerivativesContext:
        funding = session.execute(
            select(FundingRate).order_by(desc(FundingRate.funding_time)).limit(1)
        ).scalar_one_or_none()

        oi_rows = session.execute(
            select(OpenInterest).order_by(desc(OpenInterest.timestamp)).limit(24)
        ).scalars().all()

        ls = session.execute(
            select(LongShortRatio)
            .where(LongShortRatio.ratio_type == "global")
            .order_by(desc(LongShortRatio.timestamp))
            .limit(1)
        ).scalar_one_or_none()

        taker = session.execute(
            select(TakerVolume).order_by(desc(TakerVolume.timestamp)).limit(1)
        ).scalar_one_or_none()

        funding_rate = funding.funding_rate if funding else None
        funding_signal = "neutral"
        if funding_rate is not None:
            if funding_rate > 0.0005:
                funding_signal = "overleveraged_long"
            elif funding_rate < -0.0003:
                funding_signal = "overleveraged_short"
            elif funding_rate > 0:
                funding_signal = "slightly_bullish"
            else:
                funding_signal = "slightly_bearish"

        oi_change = None
        oi_signal = "neutral"
        if len(oi_rows) >= 2:
            latest_oi = oi_rows[0].open_interest
            prev_oi = oi_rows[-1].open_interest
            if prev_oi:
                oi_change = round((latest_oi - prev_oi) / prev_oi * 100, 2)
                if oi_change > 5:
                    oi_signal = "increasing"
                elif oi_change < -5:
                    oi_signal = "decreasing"

        ls_ratio = ls.long_short_ratio if ls else None
        ls_signal = "neutral"
        if ls_ratio is not None:
            if ls_ratio > 1.5:
                ls_signal = "crowded_long"
            elif ls_ratio < 0.7:
                ls_signal = "crowded_short"

        taker_ratio = taker.buy_sell_ratio if taker else None
        taker_signal = "neutral"
        if taker_ratio is not None:
            if taker_ratio > 1.1:
                taker_signal = "buyers_dominant"
            elif taker_ratio < 0.9:
                taker_signal = "sellers_dominant"

        return DerivativesContext(
            funding_rate=funding_rate,
            funding_signal=funding_signal,
            open_interest_change_pct=oi_change,
            oi_signal=oi_signal,
            long_short_ratio=ls_ratio,
            ls_signal=ls_signal,
            taker_buy_sell_ratio=taker_ratio,
            taker_signal=taker_signal,
        )

    def _coinex_context(self, session: Session) -> CoinExContext | None:
        if not settings.coinex_enabled:
            return None

        row = session.execute(
            select(CoinExFuturesSnapshot)
            .where(CoinExFuturesSnapshot.market == settings.coinex_market)
            .order_by(desc(CoinExFuturesSnapshot.collected_at))
            .limit(1)
        ).scalar_one_or_none()
        if not row:
            return None

        score = 0.0
        notes: list[str] = []

        if row.premium_pct > 0.03:
            score += 12
            notes.append(f"premium mosbat {row.premium_pct:.3f}%")
        elif row.premium_pct < -0.03:
            score -= 12
            notes.append(f"premium manfi {row.premium_pct:.3f}%")

        if row.funding_rate > 0.0001:
            score += 8
            notes.append(f"funding mosbat {row.funding_rate * 100:.4f}%")
        elif row.funding_rate < -0.0001:
            score -= 8
            notes.append(f"funding manfi {row.funding_rate * 100:.4f}%")

        if row.taker_buy_sell_ratio > 1.1:
            score += 18
            notes.append("kharid ticker ghalab dar CoinEx")
        elif row.taker_buy_sell_ratio < 0.9:
            score -= 18
            notes.append("forush ticker ghalab dar CoinEx")

        if row.oi_change_pct is not None:
            if row.oi_change_pct > 2:
                score += 8
                notes.append(f"OI ro be roshd {row.oi_change_pct:+.1f}%")
            elif row.oi_change_pct < -2:
                score -= 8
                notes.append(f"OI ro be kahesh {row.oi_change_pct:+.1f}%")

        if score >= 12:
            signal = "bullish"
            bias_label = "feshar soudi CoinEx Futures"
        elif score <= -12:
            signal = "bearish"
            bias_label = "feshar nozooli CoinEx Futures"
        else:
            signal = "neutral"
            bias_label = "konsi CoinEx Futures"

        if not notes:
            research_note = "dade CoinEx bedoon signal ghavi"
        else:
            research_note = " | ".join(notes)

        return CoinExContext(
            market=row.market,
            last_price=row.last_price,
            mark_price=row.mark_price,
            index_price=row.index_price,
            premium_pct=row.premium_pct,
            funding_rate=row.funding_rate,
            next_funding_rate=row.next_funding_rate,
            open_interest=row.open_interest,
            oi_change_pct=row.oi_change_pct,
            taker_buy_sell_ratio=row.taker_buy_sell_ratio,
            signal=signal,
            bias_label=bias_label,
            research_note=research_note,
        )

    def _sentiment_context(self, session: Session) -> SentimentContext:
        fg = session.execute(
            select(FearGreedIndex).order_by(desc(FearGreedIndex.timestamp)).limit(1)
        ).scalar_one_or_none()

        if not fg:
            return SentimentContext(None, None, "neutral")

        signal = "neutral"
        if fg.value >= 75:
            signal = "extreme_greed"
        elif fg.value >= 55:
            signal = "greed"
        elif fg.value <= 25:
            signal = "extreme_fear"
        elif fg.value <= 45:
            signal = "fear"

        return SentimentContext(fg.value, fg.classification, signal)

    def _onchain_context(self, session: Session) -> OnChainContext | None:
        aa_rows = session.execute(
            select(OnChainMetric)
            .where(OnChainMetric.metric_name == "active_addresses")
            .order_by(desc(OnChainMetric.timestamp))
            .limit(8)
        ).scalars().all()

        mvrv_row = session.execute(
            select(OnChainMetric)
            .where(OnChainMetric.metric_name == "mvrv")
            .order_by(desc(OnChainMetric.timestamp))
            .limit(1)
        ).scalar_one_or_none()

        if not aa_rows and not mvrv_row:
            return None

        active = int(aa_rows[0].value) if aa_rows else None
        aa_change = None
        aa_signal = "neutral"
        if len(aa_rows) >= 2 and aa_rows[-1].value:
            aa_change = round(
                (aa_rows[0].value - aa_rows[-1].value) / aa_rows[-1].value * 100, 2
            )
            if aa_change > 5:
                aa_signal = "growing"
            elif aa_change < -5:
                aa_signal = "declining"

        mvrv = mvrv_row.value if mvrv_row else None
        mvrv_signal = "neutral"
        if mvrv is not None:
            if mvrv > 3.0:
                mvrv_signal = "overvalued"
            elif mvrv > 2.0:
                mvrv_signal = "elevated"
            elif mvrv < 1.0:
                mvrv_signal = "undervalued"
            else:
                mvrv_signal = "fair_value"

        return OnChainContext(
            active_addresses=active,
            active_addresses_change_pct=aa_change,
            mvrv=round(mvrv, 3) if mvrv is not None else None,
            mvrv_signal=mvrv_signal,
            active_addresses_signal=aa_signal,
        )

    def _macro_context(self, session: Session) -> MacroContext | None:
        rows = session.execute(
            select(MacroMetric).order_by(desc(MacroMetric.timestamp))
        ).scalars().all()
        if not rows:
            return None

        latest_by_symbol: dict[str, MacroMetric] = {}
        for r in rows:
            if r.symbol not in latest_by_symbol:
                latest_by_symbol[r.symbol] = r

        spx = latest_by_symbol.get("spx")
        ndx = latest_by_symbol.get("ndx")
        dxy = latest_by_symbol.get("dxy")

        if not any([spx, ndx, dxy]):
            return None

        spx_signal = "neutral"
        if spx and spx.change_7d_pct > 2:
            spx_signal = "risk_on"
        elif spx and spx.change_7d_pct < -2:
            spx_signal = "risk_off"

        dxy_signal = "neutral"
        if dxy and dxy.change_7d_pct > 1:
            dxy_signal = "dollar_strength"
        elif dxy and dxy.change_7d_pct < -1:
            dxy_signal = "dollar_weakness"

        macro_bias = "neutral"
        if spx_signal == "risk_on" and dxy_signal != "dollar_strength":
            macro_bias = "bullish_crypto"
        elif spx_signal == "risk_off" or dxy_signal == "dollar_strength":
            macro_bias = "bearish_crypto"

        return MacroContext(
            spx=spx.price if spx else None,
            spx_change_7d=spx.change_7d_pct if spx else None,
            ndx=ndx.price if ndx else None,
            ndx_change_7d=ndx.change_7d_pct if ndx else None,
            dxy=dxy.price if dxy else None,
            dxy_change_7d=dxy.change_7d_pct if dxy else None,
            spx_signal=spx_signal,
            dxy_signal=dxy_signal,
            macro_bias=macro_bias,
        )

    def _liquidation_context(self, session: Session, price: float) -> LiquidationContext | None:
        rows = session.execute(
            select(LiquidationLevel)
            .where(LiquidationLevel.symbol == settings.symbol)
            .order_by(desc(LiquidationLevel.snapshot_at))
            .limit(50)
        ).scalars().all()
        if not rows:
            return None

        latest_snap = rows[0].snapshot_at
        levels = [r for r in rows if r.snapshot_at == latest_snap]
        total = sum(r.total_usd for r in levels)

        above = sorted(
            [r for r in levels if r.price_level > price],
            key=lambda x: x.total_usd,
            reverse=True,
        )[:3]
        below = sorted(
            [r for r in levels if r.price_level < price],
            key=lambda x: x.total_usd,
            reverse=True,
        )[:3]

        def _zone(r: LiquidationLevel) -> dict:
            return {
                "price": r.price_level,
                "total_usd": round(r.total_usd, 0),
                "long_usd": round(r.long_liq_usd, 0),
                "short_usd": round(r.short_liq_usd, 0),
            }

        zones_above = [_zone(r) for r in above]
        zones_below = [_zone(r) for r in below]

        nearest = None
        if levels:
            nearest_r = min(levels, key=lambda r: abs(r.price_level - price))
            nearest = _zone(nearest_r)

        signal = "neutral"
        if nearest and nearest["total_usd"] > total * 0.2:
            if nearest["price"] > price:
                signal = "liq_cluster_above"
            else:
                signal = "liq_cluster_below"

        return LiquidationContext(
            zones_above=zones_above,
            zones_below=zones_below,
            nearest_zone=nearest,
            total_24h_usd=round(total, 0),
            signal=signal,
        )

    def _build_summary(
        self,
        timeframes: dict[str, TimeframeAnalysis],
        mtf_aligned: bool,
        derivatives: DerivativesContext,
        onchain: OnChainContext | None,
        macro: MacroContext | None = None,
        liquidations: LiquidationContext | None = None,
        coinex: CoinExContext | None = None,
    ) -> str:
        tf_order = ["1w", "1d", "4h"]
        tf_labels = {"1w": "1w", "1d": "1d", "4h": "4h"}
        trend_txt = {"bullish": "soudi", "bearish": "nozooli", "neutral": "konsi"}
        trends = {tf: timeframes[tf].trend.value for tf in tf_order if tf in timeframes}

        bearish_n = sum(1 for t in trends.values() if t == "bearish")
        bullish_n = sum(1 for t in trends.values() if t == "bullish")

        if mtf_aligned and bullish_n == 3:
            verdict = "feshar soudi ghavi - se timeframe hamjahat"
        elif mtf_aligned and bearish_n == 3:
            verdict = "feshar nozooli ghavi - se timeframe hamjahat"
        elif bearish_n >= 2 and trends.get("1w") != "bullish":
            verdict = "feshar nozooli ghalab dar kohtah-madat"
        elif bullish_n >= 2 and trends.get("1w") != "bearish":
            verdict = "feshar soudi ghalab dar kohtah-madat"
        elif trends.get("1w") == "bullish" and trends.get("4h") == "bearish":
            verdict = "rend bolandmodat soudi - eslah kohtah-madat"
        elif trends.get("1w") == "bearish" and trends.get("4h") == "bullish":
            verdict = "rend bolandmodat nozooli - bazgasht kohtah-madat"
        else:
            verdict = "bazaar bedoon jahat - timeframe ha na hamahang"

        trend_line = ", ".join(
            f"{tf_labels[tf]} {trend_txt.get(trends[tf], trends[tf])}"
            for tf in tf_order
            if tf in trends
        )

        drivers: list[str] = []
        if liquidations and liquidations.signal == "liq_cluster_below":
            drivers.append("liquidation long zir gheymat")
        elif liquidations and liquidations.signal == "liq_cluster_above":
            drivers.append("liquidation short bala gheymat")

        tf4h = timeframes.get("4h")
        if tf4h:
            smc = tf4h.levels.get("smc_signal")
            if smc in ("bos_bullish", "choch_bullish"):
                drivers.append("SMC soudi dar 4h")
            elif smc in ("bos_bearish", "choch_bearish"):
                drivers.append("SMC nozooli dar 4h")

        if derivatives.funding_signal == "overleveraged_long":
            drivers.append("funding mosbat bala")
        elif derivatives.funding_signal == "overleveraged_short":
            drivers.append("funding manfi shadid")

        if onchain and onchain.mvrv_signal == "overvalued":
            drivers.append("MVRV bala az miyangin")
        elif onchain and onchain.mvrv_signal == "undervalued":
            drivers.append("MVRV paiin (arzesh nesbi)")

        if macro and macro.macro_bias == "bearish_crypto":
            drivers.append("macro manfi baraye risk")
        elif macro and macro.macro_bias == "bullish_crypto":
            drivers.append("macro mosbat baraye risk")

        if coinex and coinex.signal == "bullish":
            drivers.append(f"CoinEx: {coinex.bias_label}")
        elif coinex and coinex.signal == "bearish":
            drivers.append(f"CoinEx: {coinex.bias_label}")

        parts = [verdict, trend_line]
        if drivers:
            parts.append("avamel kelidi: " + " | ".join(drivers[:3]))
        return " - ".join(parts)

    def analyze(self, session: Session) -> OverviewAnalysis:
        timeframes: dict[str, TimeframeAnalysis] = {}
        for tf in settings.timeframes:
            df = self._load_candles(session, tf)
            timeframes[tf] = self.technical.analyze_dataframe(df, tf)

        ticker = session.execute(
            select(TickerSnapshot).order_by(desc(TickerSnapshot.timestamp)).limit(1)
        ).scalar_one_or_none()

        price = ticker.price if ticker else timeframes["4h"].price
        change_24h = ticker.price_change_pct_24h if ticker else 0.0

        scores = [timeframes[tf].score for tf in settings.timeframes]
        confidences = [timeframes[tf].confidence for tf in settings.timeframes]
        weights = {"4h": 0.25, "1d": 0.35, "1w": 0.40}
        overall_score = sum(timeframes[tf].score * weights.get(tf, 0.33) for tf in settings.timeframes)
        overall_confidence = sum(timeframes[tf].confidence * weights.get(tf, 0.33) for tf in settings.timeframes)

        trends = [timeframes[tf].trend for tf in settings.timeframes]
        mtf_aligned = len(set(trends)) == 1 and trends[0] != Trend.NEUTRAL

        derivatives = self._derivatives_context(session)
        sentiment = self._sentiment_context(session)
        onchain = self._onchain_context(session)
        macro = self._macro_context(session)
        liquidations = self._liquidation_context(session, price)
        coinex = self._coinex_context(session)
        summary = self._build_summary(
            timeframes, mtf_aligned, derivatives, onchain, macro, liquidations, coinex
        )

        if derivatives.funding_signal == "overleveraged_long" and overall_score > 60:
            overall_confidence = max(30, overall_confidence - 10)
        if sentiment.signal == "extreme_greed" and overall_score > 65:
            overall_confidence = max(30, overall_confidence - 8)
        if onchain and onchain.mvrv_signal == "overvalued" and overall_score > 60:
            overall_confidence = max(30, overall_confidence - 7)
        if macro and macro.macro_bias == "bearish_crypto" and overall_score > 55:
            overall_confidence = max(30, overall_confidence - 5)
        if macro and macro.macro_bias == "bullish_crypto" and overall_score > 55:
            overall_confidence = min(95, overall_confidence + 3)
        if coinex and coinex.signal == "bullish" and overall_score > 50:
            overall_confidence = min(95, overall_confidence + 4)
        elif coinex and coinex.signal == "bearish" and overall_score < 50:
            overall_confidence = min(95, overall_confidence + 4)
        elif coinex and coinex.signal == "bearish" and overall_score > 55:
            overall_confidence = max(30, overall_confidence - 5)

        return OverviewAnalysis(
            price=price,
            change_24h_pct=change_24h,
            overall_score=round(overall_score, 1),
            overall_confidence=round(overall_confidence, 1),
            summary=summary,
            mtf_aligned=mtf_aligned,
            timeframes=timeframes,
            derivatives=derivatives,
            sentiment=sentiment,
            updated_at=datetime.now(timezone.utc).isoformat(),
            onchain=onchain,
            macro=macro,
            liquidations=liquidations,
            coinex=coinex,
        )
