from src.analyzer.models import OverviewAnalysis, TimeframeAnalysis, Trend
from src.analyzer.forecast import Forecast4h


TREND_FA = {
    Trend.BULLISH: "صعودی",
    Trend.BEARISH: "نزولی",
    Trend.NEUTRAL: "خنثی",
}

TREND_EMOJI = {
    Trend.BULLISH: "🟢",
    Trend.BEARISH: "🔴",
    Trend.NEUTRAL: "🟡",
}


def _trend_display(trend: Trend | str) -> str:
    if isinstance(trend, str):
        trend = Trend(trend)
    return f"{TREND_EMOJI[trend]} {TREND_FA[trend]}"


def overview_message(analysis: OverviewAnalysis) -> str:
    lines = [
        "📊 <b>BTC/USDT</b>",
        "",
        f"💰 قیمت: <b>${analysis.price:,.2f}</b> ({analysis.change_24h_pct:+.2f}%)",
        f"🎯 اعتماد کلی: <b>{analysis.overall_confidence:.0f}%</b>",
        "",
        "┌─────────┬─────────┬─────────┐",
        "│ هفتگی   │ روزانه  │ 4 ساعته │",
    ]

    for tf, label in [("1w", "هفتگی"), ("1d", "روزانه"), ("4h", "4 ساعته")]:
        pass

    tf_data = []
    for tf in ["1w", "1d", "4h"]:
        t = analysis.timeframes[tf]
        trend = t.trend
        if isinstance(trend, str):
            trend = Trend(trend)
        tf_data.append(f"{TREND_EMOJI[trend]} {t.score:.0f}")

    lines[6] = f"│ {tf_data[0]:^7} │ {tf_data[1]:^7} │ {tf_data[2]:^7} │"
    lines.append("└─────────┴─────────┴─────────┘")
    lines.append("")
    lines.append(f"📌 {analysis.summary}")

    d = analysis.derivatives
    if d.funding_rate is not None:
        lines.append(f"📈 Funding: {d.funding_rate * 100:.4f}%")

    s = analysis.sentiment
    if s.fear_greed_value is not None:
        lines.append(f"😱 Fear & Greed: {s.fear_greed_value} ({s.fear_greed_label})")

    lines.append("")
    lines.append("⚠️ تحلیل است، نه توصیه سرمایه‌گذاری")
    return "\n".join(lines)


def forecast_4h_message(forecast: Forecast4h) -> str:
    dir_emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(
        forecast.direction, "🟡"
    )
    conf_bar = "█" * int(forecast.confidence / 10) + "░" * (10 - int(forecast.confidence / 10))

    lines = [
        "╔══════════════════════════════════╗",
        "║  <b>پیش‌بینی روند — ۴ ساعت آینده</b>  ║",
        "╚══════════════════════════════════╝",
        "",
        f"💰 قیمت فعلی: <b>${forecast.price:,.0f}</b>",
        "",
        f"{dir_emoji} جهت: <b>{forecast.direction_label}</b>",
        f"📊 امتیاز جهت: <b>{forecast.direction_score:+.1f}</b>",
        f"🎯 اعتماد مدل: <b>{forecast.confidence:.0f}%</b>",
        f"<code>{conf_bar}</code>",
        "",
        "┏━━━━━━━━ <b>سطوح کلیدی</b> ━━━━━━━━┓",
    ]

    if forecast.support:
        lines.append(f"┃ 🟢 حمایت: <b>${forecast.support:,.0f}</b>")
    if forecast.resistance:
        lines.append(f"┃ 🔴 مقاومت: <b>${forecast.resistance:,.0f}</b>")
    if forecast.primary_target:
        label = "هدف نزولی" if forecast.direction == "bearish" else "هدف صعودی" if forecast.direction == "bullish" else "هدف محتمل"
        lines.append(f"┃ 🎯 {label}: <b>${forecast.primary_target:,.0f}</b>")
    if forecast.invalidation:
        lines.append(f"┃ ⚠️ باطل‌کننده: <b>${forecast.invalidation:,.0f}</b>")
    lines.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")

    lines.extend(["", "🟢 <b>دلایل صعودی</b>"])
    for r in forecast.bullish_reasons:
        lines.append(f"  • {r}")

    lines.extend(["", "🔴 <b>ریسک‌ها</b>"])
    for r in forecast.risks:
        lines.append(f"  • {r}")

    lines.extend([
        "",
        "┏━━━━━━━━ <b>جمع‌بندی</b> ━━━━━━━━┓",
        f"┃ {forecast.summary}",
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        "",
        "⚠️ تحلیل است، نه توصیه سرمایه‌گذاری",
    ])
    return "\n".join(lines)


def timeframe_message(tf_analysis: TimeframeAnalysis) -> str:
    trend = tf_analysis.trend
    if isinstance(trend, str):
        trend = Trend(trend)

    tf_labels = {"4h": "4 ساعته", "1d": "روزانه", "1w": "هفتگی"}
    ind = tf_analysis.indicators

    lines = [
        f"📉 <b>تحلیل {tf_labels.get(tf_analysis.timeframe, tf_analysis.timeframe)}</b>",
        "",
        f"روند: {_trend_display(trend)}",
        f"امتیاز: {tf_analysis.score:.0f}/100 | اعتماد: {tf_analysis.confidence:.0f}%",
        f"رژیم: {tf_analysis.regime.value}",
        "",
        "اندیکاتورها:",
    ]

    if ind.get("ema50"):
        lines.append(f"• EMA50: ${ind['ema50']:,.2f}")
    if ind.get("rsi"):
        lines.append(f"• RSI: {ind['rsi']:.1f}")
    if ind.get("macd_hist") is not None:
        macd_label = "مثبت" if ind["macd_hist"] > 0 else "منفی"
        lines.append(f"• MACD: {macd_label}")
    if ind.get("adx"):
        lines.append(f"• ADX: {ind['adx']:.1f}")
    if ind.get("volume_ratio"):
        lines.append(f"• حجم/میانگین: {ind['volume_ratio']:.2f}x")
    if ind.get("stoch_k"):
        lines.append(f"• Stochastic K: {ind['stoch_k']:.1f}")
    if ind.get("bb_signal"):
        lines.append(f"• Bollinger: {ind['bb_signal']}")

    lv = tf_analysis.levels or {}
    if lv.get("support"):
        lines.append(f"\nحمایت: ${lv['support']:,.0f}")
    if lv.get("resistance"):
        lines.append(f"مقاومت: ${lv['resistance']:,.0f}")
    if lv.get("fib_nearest"):
        lines.append(f"فیبوناچی: {lv['fib_nearest']}")

    lines.append(f"\nساختار: {tf_analysis.structure}")
    return "\n".join(lines)


def signal_alert(analysis: OverviewAnalysis, tf: str) -> str:
    t = analysis.timeframes[tf]
    trend = t.trend
    if isinstance(trend, str):
        trend = Trend(trend)

    tf_labels = {"4h": "4 ساعته", "1d": "روزانه", "1w": "هفتگی"}
    return (
        f"🚨 <b>سیگنال جدید — {tf_labels.get(tf, tf)}</b>\n\n"
        f"{_trend_display(trend)} | اعتماد: {t.confidence:.0f}%\n"
        f"💰 قیمت: ${analysis.price:,.2f}\n"
        f"📌 {analysis.summary}\n\n"
        f"⚠️ تحلیل است، نه توصیه سرمایه‌گذاری"
    )


def advisor_message(insight) -> str:
    lines = [
        "🤖 <b>مشاور هوش مصنوعی داشبورد</b>",
        "",
        f"📌 {insight.headline}",
        f"<i>{insight.confidence_note}</i>",
        "",
    ]

    if insight.problems:
        lines.append("⚠️ <b>مشکلات</b>")
        for p in insight.problems:
            lines.append(f"  • {p}")
        lines.append("")

    if insight.conflicts:
        lines.append("⚡ <b>تناقض‌ها</b>")
        for c in insight.conflicts:
            lines.append(f"  • {c}")
        lines.append("")

    if insight.ideas:
        lines.append("💡 <b>ایده‌ها</b>")
        for idea in insight.ideas:
            lines.append(f"  • {idea}")
        lines.append("")

    if insight.watch_levels:
        lines.append("🎯 <b>سطوح کلیدی</b>")
        for lv in insight.watch_levels:
            price = lv.get("price")
            reason = lv.get("reason", "")
            if price:
                lines.append(f"  • ${price:,.0f} — {reason}")
        lines.append("")

    lines.append("💬 هر سوالی داری بپرس — من داشبورد رو می‌بینم.")
    lines.append("⚠️ تحلیل است، نه توصیه سرمایه‌گذاری")
    return "\n".join(lines)


def advisor_alert_message(insight) -> str:
    lines = [
        "🔔 <b>هشدار مشاور — مشکل در داشبورد</b>",
        "",
        f"📌 {insight.headline}",
        "",
    ]

    if insight.conflicts:
        lines.append("⚡ <b>تناقض‌ها</b>")
        for c in insight.conflicts[:3]:
            lines.append(f"  • {c}")
        lines.append("")

    real_problems = [p for p in insight.problems if "مشکل بحرانی دیده نشد" not in p]
    if real_problems:
        lines.append("⚠️ <b>مشکلات</b>")
        for p in real_problems[:4]:
            lines.append(f"  • {p}")
        lines.append("")

    lines.append("برای جزئیات: /advisor")
    lines.append("یا مستقیم سوالت رو بپرس 💬")
    return "\n".join(lines)
