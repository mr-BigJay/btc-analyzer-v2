const TREND_FA = { bullish: "صعودی", bearish: "نزولی", neutral: "خنثی" };
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

function updateOverview(data) {
  document.getElementById("price").textContent = formatPrice(data.price);
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
  const BIAS_FA = {
    bullish_crypto: "مثبت BTC",
    bearish_crypto: "منفی BTC",
    neutral: "خنثی",
  };
  if (macro) {
    document.getElementById("spx").textContent =
      macro.spx != null ? `${macro.spx.toFixed(0)} (${macro.spx_change_7d:+.1f}%)` : "—";
    document.getElementById("ndx").textContent =
      macro.ndx != null ? `${macro.ndx.toFixed(0)} (${macro.ndx_change_7d:+.1f}%)` : "—";
    document.getElementById("dxy").textContent =
      macro.dxy != null ? `${macro.dxy.toFixed(2)} (${macro.dxy_change_7d:+.1f}%)` : "—";
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

async function refresh() {
  try {
    const [overview, backtest, liq, optParams] = await Promise.all([
      fetchOverview(),
      fetchBacktest(),
      fetchLiquidations(),
      fetchOptimizedParams(),
    ]);
    updateOverview(overview);
    updateBacktest(backtest);
    renderLiquidations(liq);
    updateOptimizedParams(optParams);
    await loadChart(currentTf);
  } catch (e) {
    console.error(e);
    document.getElementById("updated-at").textContent = "خطا در دریافت داده";
  }
}

initChart();
refresh();
setInterval(refresh, 5 * 60 * 1000);
