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
    const overview = await fetchOverview();
    updateOverview(overview);
    await loadChart(currentTf);
  } catch (e) {
    console.error(e);
    document.getElementById("updated-at").textContent = "خطا در دریافت داده";
  }
}

initChart();
refresh();
setInterval(refresh, 5 * 60 * 1000);
