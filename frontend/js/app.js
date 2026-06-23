const TREND_FA = { bullish: "صعودی", bearish: "نزولی", neutral: "خنثی" };
const BIAS_FA = {
  bullish_crypto: "مثبت BTC",
  bearish_crypto: "منفی BTC",
  neutral: "خنثی",
};
let chart, candleSeries, currentTf = "4h";

async function fetchOverview() {
  const res = await fetch("/api/v1/overview");
  if (!res.ok) throw new Error("overview failed");
  return res.json();
}

async function fetchChart(tf) {
  const res = await fetch(`/api/v1/chart/${tf}?limit=120`);
  if (!res.ok) throw new Error("chart failed");
  return res.json();
}

async function fetchBacktest() {
  const res = await fetch("/api/v1/backtest?limit=3");
  if (!res.ok) return [];
  return res.json();
}

async function fetchLiquidations() {
  const res = await fetch("/api/v1/liquidations");
  if (!res.ok) return null;
  return res.json();
}

async function fetchOptimizedParams() {
  const res = await fetch("/api/v1/optimized-params");
  if (!res.ok) return {};
  return res.json();
}

function formatPrice(n) {
  return "$" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function chip(text, cls = "") {
  return `<span class="tech-chip ${cls}">${text}</span>`;
}

function trendClass(trend) {
  return trend === "bullish" ? "bull" : trend === "bearish" ? "bear" : "warn";
}

function regimeFa(regime) {
  return { trending: "روندی", ranging: "رنج", volatile: "پرنوسان" }[regime] || regime;
}

function buildTechnicalBrief(data, liq, backtest) {
  const tf4h = data.timeframes["4h"];
  const tf1d = data.timeframes["1d"];
  const tf1w = data.timeframes["1w"];
  const d = data.derivatives;
  const s = data.sentiment;
  const oc = data.onchain;
  const macro = data.macro;
  const lv = tf4h.levels || {};

  const mtfNote = data.mtf_aligned
    ? "سه تایم‌فریم در یک جهت هم‌راستا هستند و سیگنال MTF Confluence تقویت می‌شود"
    : "تایم‌فریم‌ها در یک جهت نیستند؛ سیگنال کوتاه‌مدت ممکن است با روند بلندمدت در تضاد باشد";

  const funding =
    d.funding_rate != null
      ? chip(`${(d.funding_rate * 100).toFixed(4)}% funding`, d.funding_signal === "bullish" ? "bull" : d.funding_signal === "bearish" ? "bear" : "dim")
      : chip("funding نامشخص", "dim");

  const oi =
    d.open_interest_change_pct != null
      ? chip(`OI ${d.open_interest_change_pct > 0 ? "+" : ""}${d.open_interest_change_pct}%`, d.oi_signal === "bullish" ? "bull" : d.oi_signal === "bearish" ? "bear" : "dim")
      : "";

  const ls =
    d.long_short_ratio != null
      ? chip(`L/S ${d.long_short_ratio.toFixed(2)}`, d.ls_signal === "bullish" ? "bull" : d.ls_signal === "bearish" ? "bear" : "dim")
      : "";

  const fg =
    s.fear_greed_value != null
      ? chip(`F&G ${s.fear_greed_value}`, s.signal === "bullish" ? "bull" : s.signal === "bearish" ? "bear" : "warn")
      : "";

  const mvrv =
    oc?.mvrv != null
      ? chip(`MVRV ${oc.mvrv}`, oc.mvrv_signal === "bullish" ? "bull" : oc.mvrv_signal === "bearish" ? "bear" : "dim")
      : "";

  const macroPart =
    macro && macro.dxy_change_7d != null && macro.spx_change_7d != null
      ? `محیط ماکرو با بایاس ${chip(BIAS_FA[macro.macro_bias] || macro.macro_bias, macro.macro_bias === "bullish_crypto" ? "bull" : macro.macro_bias === "bearish_crypto" ? "bear" : "warn")} — DXY هفتگی ${chip((macro.dxy_change_7d >= 0 ? "+" : "") + macro.dxy_change_7d.toFixed(1) + "%", macro.dxy_change_7d > 0 ? "bear" : "bull")} و SPX ${chip((macro.spx_change_7d >= 0 ? "+" : "") + macro.spx_change_7d.toFixed(1) + "%", macro.spx_change_7d > 0 ? "bull" : "bear")}`
      : "";

  const smcPart = lv.smc_signal && lv.smc_signal !== "none"
    ? `ساختار SMC در 4h نشان‌دهنده ${chip(lv.smc_signal.replace(/_/g, " "), lv.smc_signal.includes("bull") ? "bull" : "bear")} است`
    : "ساختار SMC فعلاً بدون شکست ساختاری معنادار است";

  const levelsPart =
    lv.support != null && lv.resistance != null
      ? `باند قیمتی میان ${chip(formatPrice(lv.support), "bull")} (حمایت) و ${chip(formatPrice(lv.resistance), "bear")} (مقاومت)`
      : "";

  const liqPart =
    liq?.zones?.length
      ? `نقشه لیکوئیدیشن OKX تمرکز نقدینگی اجباری را در محدوده‌های نزدیک قیمت فعلی نشان می‌دهد — ${chip(liq.zones.length + " زون", "dim")}`
      : data.liquidations?.signal
        ? chip(data.liquidations.signal, "warn")
        : "";

  const bt = backtest?.[0];
  const btPart = bt
    ? `بک‌تست walk-forward روی ${chip(bt.timeframe, "dim")} با Win Rate ${chip(bt.win_rate + "%", bt.win_rate >= 55 ? "bull" : "warn")} و Profit Factor ${chip(String(bt.profit_factor), bt.profit_factor >= 1.5 ? "bull" : "warn")} اعتبار سیگنال را ${bt.profit_factor >= 1.5 ? "تأیید" : "با احتیاط"} می‌کند`
    : "";

  return [
    `بیت‌کوین در ${chip(formatPrice(data.price), "dim")} با تغییر ۲۴ساعته ${chip((data.change_24h_pct >= 0 ? "+" : "") + data.change_24h_pct.toFixed(2) + "%", data.change_24h_pct >= 0 ? "bull" : "bear")} معامله می‌شود؛`,
    `امتیاز کلی ${chip(data.overall_score.toFixed(0) + "/100", data.overall_score >= 55 ? "bull" : data.overall_score <= 45 ? "bear" : "warn")} با اعتماد ${chip(data.overall_confidence.toFixed(0) + "%", "dim")} از ترکیب پنج لایه تحلیل (روند، مومنتوم، حجم، نوسان، ساختار) به‌دست آمده است.`,
    `در MTF، روند ${chip(TREND_FA[tf1w.trend], trendClass(tf1w.trend))} هفتگی، ${chip(TREND_FA[tf1d.trend], trendClass(tf1d.trend))} روزانه و ${chip(TREND_FA[tf4h.trend], trendClass(tf4h.trend))} در 4h دیده می‌شود — رژیم 4h: ${chip(regimeFa(tf4h.regime), "dim")}؛ ${mtfNote}.`,
    levelsPart,
    smcPart + (lv.fib_nearest ? ` و نزدیک‌ترین سطح فیبوناچی ${chip(lv.fib_nearest, "warn")} قرار دارد` : "") + ".",
    `بازار مشتقات: ${funding}${oi ? "، " + oi : ""}${ls ? "، " + ls : ""}.`,
    macroPart ? macroPart + "." : "",
    oc
      ? `آنچین: ${mvrv || chip("—", "dim")}${oc.active_addresses != null ? " و آدرس‌های فعال " + chip(oc.active_addresses.toLocaleString(), "dim") : ""}${fg ? "؛ احساسات بازار " + fg : ""}.`
      : fg
        ? `احساسات بازار ${fg}.`
        : "",
    liqPart ? liqPart + "." : "",
    btPart ? btPart + "." : "",
    `داده‌ها هر ۱۵ دقیقه از OKX، CoinMetrics، Yahoo Finance و Deribit جمع‌آوری و بدون ورودی دستی تحلیل می‌شوند — این متن جایگزین مشاوره مالی نیست.`
  ]
    .filter(Boolean)
    .join(" ");
}

function updateTechnicalBrief(data, liq, backtest) {
  const el = document.getElementById("tech-brief");
  if (!el) return;
  el.innerHTML = buildTechnicalBrief(data, liq, backtest);
  el.classList.remove("muted");
}

function updateOverview(data) {
  const changeEl = document.getElementById("change");
  const ch = Number(data.change_24h_pct);
  changeEl.textContent = `${ch >= 0 ? "+" : ""}${ch.toFixed(2)}% (24h)`;
  changeEl.className = "change " + (ch >= 0 ? "up" : "down");

  document.getElementById("confidence").textContent = `${data.overall_confidence.toFixed(0)}%`;
  document.getElementById("score").textContent = `امتیاز: ${data.overall_score.toFixed(0)}/100`;
  document.getElementById("summary").textContent = data.summary;
  document.getElementById("mtf-badge").textContent = data.mtf_aligned
    ? "✅ هم‌راستایی MTF"
    : "⚠️ ناهماهنگی بین تایم‌فریم‌ها";
  document.getElementById("updated-at").textContent =
    "آخرین بروزرسانی: " + new Date(data.updated_at).toLocaleString("fa-IR");

  for (const tf of ["1w", "1d", "4h"]) {
    const t = data.timeframes[tf];
    const card = document.getElementById(`card-${tf}`);
    const trendEl = card.querySelector(".trend");
    trendEl.textContent = TREND_FA[t.trend] || t.trend;
    trendEl.className = "trend " + t.trend;
    card.querySelector(".fill").style.width = `${t.score}%`;
    card.querySelector(".score-text").textContent = `${t.score.toFixed(0)}/100 — اعتماد ${t.confidence.toFixed(0)}%`;
  }

  const d = data.derivatives;
  document.getElementById("funding").textContent =
    d.funding_rate != null ? `${(d.funding_rate * 100).toFixed(4)}%` : "—";
  document.getElementById("oi").textContent =
    d.open_interest_change_pct != null ? `${d.open_interest_change_pct}%` : "—";
  document.getElementById("ls").textContent =
    d.long_short_ratio != null ? d.long_short_ratio.toFixed(2) : "—";

  const s = data.sentiment;
  document.getElementById("fg").textContent =
    s.fear_greed_value != null ? `${s.fear_greed_value} (${s.fear_greed_label})` : "—";

  const oc = data.onchain;
  if (oc) {
    document.getElementById("mvrv").textContent =
      oc.mvrv != null ? `${oc.mvrv} (${oc.mvrv_signal})` : "—";
    document.getElementById("active-addr").textContent =
      oc.active_addresses != null
        ? `${oc.active_addresses.toLocaleString()} (${oc.active_addresses_signal})`
        : "—";
  }

  const macro = data.macro;
  if (macro) {
    document.getElementById("spx").textContent =
      macro.spx != null ? `${macro.spx.toFixed(0)} (${macro.spx_change_7d >= 0 ? "+" : ""}${macro.spx_change_7d.toFixed(1)}%)` : "—";
    document.getElementById("ndx").textContent =
      macro.ndx != null ? `${macro.ndx.toFixed(0)} (${macro.ndx_change_7d >= 0 ? "+" : ""}${macro.ndx_change_7d.toFixed(1)}%)` : "—";
    document.getElementById("dxy").textContent =
      macro.dxy != null ? `${macro.dxy.toFixed(2)} (${macro.dxy_change_7d >= 0 ? "+" : ""}${macro.dxy_change_7d.toFixed(1)}%)` : "—";
    document.getElementById("macro-bias").textContent =
      BIAS_FA[macro.macro_bias] || macro.macro_bias;
  }

  const tf4h = data.timeframes["4h"];
  const lv = tf4h.levels || {};
  document.getElementById("support").textContent =
    lv.support != null ? formatPrice(lv.support) : "—";
  document.getElementById("resistance").textContent =
    lv.resistance != null ? formatPrice(lv.resistance) : "—";
  document.getElementById("fib-level").textContent =
    lv.fib_nearest ? `${lv.fib_nearest} (${lv.fib_signal || ""})` : "—";

  const SMC_FA = {
    bos_bullish: "BOS صعودی", bos_bearish: "BOS نزولی",
    choch_bullish: "CHoCH صعودی", choch_bearish: "CHoCH نزولی", none: "—",
  };
  document.getElementById("smc-signal").textContent =
    SMC_FA[lv.smc_signal] || lv.smc_signal || "—";
  const fvg = lv.active_fvg;
  document.getElementById("fvg-active").textContent = fvg
    ? `${fvg.type} (${fvg.bottom?.toFixed(0)}–${fvg.top?.toFixed(0)})` : "—";
  const ob = lv.nearest_ob;
  document.getElementById("order-block").textContent = ob
    ? `${ob.type} (${ob.bottom?.toFixed(0)}–${ob.top?.toFixed(0)})` : "—";
}

function renderLiquidations(data) {
  const el = document.getElementById("liq-map");
  if (!data || !data.zones.length) {
    el.textContent = "منتظر جمع‌آوری خودکار...";
    return;
  }
  const maxTotal = Math.max(...data.zones.map((z) => z.total_usd), 1);
  el.innerHTML = data.zones
    .slice(-12)
    .map((z) => {
      const pct = (z.total_usd / maxTotal) * 100;
      const cls = z.long_usd > z.short_usd ? "liq-long" : "liq-short";
      return `<div class="liq-bar-row">
        <span>$${z.price.toLocaleString()}</span>
        <div class="liq-bar-bg"><div class="liq-bar-fill ${cls}" style="width:${pct}%"></div></div>
        <span>$${(z.total_usd / 1000).toFixed(0)}k</span>
      </div>`;
    })
    .join("");
}

function updateOptimizedParams(params) {
  const el = document.getElementById("optimized-params");
  const keys = Object.keys(params);
  if (!keys.length) {
    el.textContent = "بهینه‌سازی خودکار با scheduler اجرا می‌شود";
    return;
  }
  el.innerHTML = keys
    .map(
      (tf) => `<div class="backtest-item">
        <strong>${tf} — پارامتر بهینه</strong>
        <span>اعتماد: ${params[tf].confidence}</span>
        <span>WR: ${params[tf].win_rate}%</span>
        <span>PF: ${params[tf].profit_factor}</span>
      </div>`
    )
    .join("");
}

function updateBacktest(rows) {
  const el = document.getElementById("backtest-results");
  if (!rows.length) {
    el.textContent = "بک‌تست خودکار با scheduler اجرا می‌شود";
    return;
  }
  el.innerHTML = rows
    .map(
      (r) => `
    <div class="backtest-item">
      <strong>${r.timeframe}</strong>
      <span>سیگنال: ${r.total_signals}</span>
      <span>Win rate: ${r.win_rate}%</span>
      <span>PF: ${r.profit_factor}</span>
      <span>Avg: ${r.avg_return_pct}%</span>
    </div>`
    )
    .join("");
}

function initChart() {
  const container = document.getElementById("chart-container");
  chart = LightweightCharts.createChart(container, {
    layout: { background: { color: "#161b22" }, textColor: "#e6edf3" },
    grid: { vertLines: { color: "#30363d" }, horzLines: { color: "#30363d" } },
    width: container.clientWidth,
    height: container.clientHeight,
  });
  candleSeries = chart.addCandlestickSeries({
    upColor: "#26a69a",
    downColor: "#ef5350",
    borderVisible: false,
    wickUpColor: "#26a69a",
    wickDownColor: "#ef5350",
  });
  window.addEventListener("resize", () => {
    chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
  });
}

async function loadChart(tf) {
  currentTf = tf;
  const data = await fetchChart(tf);
  const candles = data.candles.map((c) => ({
    time: Math.floor(new Date(c.time).getTime() / 1000),
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  }));
  candleSeries.setData(candles);
  chart.timeScale().fitContent();
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    loadChart(btn.dataset.tf);
  });
});

async function fetchForecast() {
  const res = await fetch("/api/v1/forecast/4h");
  if (!res.ok) throw new Error("forecast failed");
  return res.json();
}

function fmtUsd(n) {
  if (n == null) return "—";
  return "$" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function updateForecast(fc) {
  const dirEl = document.getElementById("forecast-direction");
  dirEl.textContent = fc.direction_label;
  dirEl.className = "forecast-direction " + fc.direction;

  document.getElementById("fc-price").textContent = fmtUsd(fc.price);
  const scoreEl = document.getElementById("fc-score");
  scoreEl.textContent = (fc.direction_score >= 0 ? "+" : "") + fc.direction_score.toFixed(1);
  scoreEl.style.color = fc.direction_score >= 0 ? "#3dd6c5" : "#ff8a80";

  document.getElementById("fc-confidence").textContent = fc.confidence.toFixed(0) + "%";
  document.getElementById("fc-conf-bar").style.width = fc.confidence + "%";

  document.getElementById("fc-support").textContent = fmtUsd(fc.support);
  document.getElementById("fc-resistance").textContent = fmtUsd(fc.resistance);

  const targetLabel = document.getElementById("fc-target-label");
  if (fc.direction === "bearish") targetLabel.textContent = "هدف نزولی";
  else if (fc.direction === "bullish") targetLabel.textContent = "هدف صعودی";
  else targetLabel.textContent = "هدف محتمل";

  document.getElementById("fc-target").textContent = fmtUsd(fc.primary_target);
  document.getElementById("fc-invalidation").textContent = fmtUsd(fc.invalidation);

  const tags = [
    fc.cvd_signal,
    fc.options_flow,
    fc.gamma_regime_label,
    fc.whale_signal,
  ].filter(Boolean);
  if (fc.put_wall) tags.push(`Put Wall ${fmtUsd(fc.put_wall)}`);
  if (fc.call_wall) tags.push(`Call Wall ${fmtUsd(fc.call_wall)}`);

  document.getElementById("fc-tags").innerHTML = tags
    .map((t) => `<span class="fc-tag">${t}</span>`)
    .join("");

  document.getElementById("fc-bullish").innerHTML = fc.bullish_reasons
    .map((r) => `<li>${r}</li>`)
    .join("");
  document.getElementById("fc-risks").innerHTML = fc.risks
    .map((r) => `<li>${r}</li>`)
    .join("");
  document.getElementById("fc-summary").textContent = fc.summary;
}

async function refresh() {
  try {
    const [overview, backtest, liq, optParams, forecast] = await Promise.all([
      fetchOverview(),
      fetchBacktest(),
      fetchLiquidations(),
      fetchOptimizedParams(),
      fetchForecast(),
    ]);
    updateOverview(overview);
    updateForecast(forecast);
    updateBacktest(backtest);
    renderLiquidations(liq);
    updateOptimizedParams(optParams);
    updateTechnicalBrief(overview, liq, backtest);
    await loadChart(currentTf);
  } catch (e) {
    console.error(e);
    document.getElementById("updated-at").textContent = "خطا در دریافت داده";
  }
}

initChart();
refresh();
setInterval(refresh, 5 * 60 * 1000);
