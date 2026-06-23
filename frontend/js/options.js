const REFRESH_MS = 5 * 60 * 1000;

async function fetchLatest() {
  const res = await fetch("/api/v1/options/latest");
  if (!res.ok) throw new Error("options latest failed");
  return res.json();
}

function formatUsd(n) {
  if (n == null) return "—";
  return "$" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function renderScreener(data) {
  const screener = data.screener;
  document.getElementById("spot-price").textContent = `BTC: ${formatUsd(screener.spot_current)}`;
  document.getElementById("updated-at").textContent =
    "بروزرسانی: " + new Date(data.updated_at).toLocaleString("fa-IR");

  const modeLabels = { private: "🔐 Private", public: "📊 Public" };
  document.getElementById("mode-badge").textContent = modeLabels[data.mode] || data.mode;

  if (!screener.summary) return;
  document.getElementById("sum-count").textContent = screener.summary.position_count;
  document.getElementById("sum-size").textContent = screener.summary.total_size;
  document.getElementById("sum-value").textContent = formatUsd(screener.summary.total_entry_value_usd);

  const tbody = document.getElementById("screener-body");
  if (!screener.rows.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="muted">داده‌ای نیست — منتظر جمع‌آوری</td></tr>';
    return;
  }

  tbody.innerHTML = screener.rows
    .map(
      (r) => `
    <tr>
      <td class="type-${r.option_type}">${r.option_type.toUpperCase()}</td>
      <td>${r.expiry_utc}</td>
      <td>${r.strike.toLocaleString()}</td>
      <td>${formatUsd(r.underlying)}</td>
      <td>${r.price_btc.toFixed(4)} / ${r.iv.toFixed(1)}%</td>
      <td class="side-${r.side}">${r.side}</td>
      <td>${r.size}</td>
      <td>${formatUsd(r.entry_value_usd)}</td>
      <td>${r.entry_date}</td>
    </tr>`
    )
    .join("");
}

function renderRiskChart(data) {
  const risk = data.risk_profile;
  if (!risk.points.length) {
    document.getElementById("risk-chart").innerHTML =
      '<p class="muted" style="padding:2rem">منتظر جمع‌آوری خودکار...</p>';
    return;
  }

  const spots = risk.points.map((p) => p.spot);
  const spot = risk.spot_current;

  const traces = [
    { name: "PnL (USD)", y: risk.points.map((p) => p.pnl), line: { color: "#58a6ff", width: 2.5 } },
    { name: "Delta", y: risk.points.map((p) => p.delta), line: { color: "#26a69a", width: 1.5 } },
    { name: "Gamma×1000", y: risk.points.map((p) => p.gamma * 1000), line: { color: "#f0b429", width: 1.5 } },
    { name: "Theta", y: risk.points.map((p) => p.theta), line: { color: "#ef5350", width: 1.5 } },
    { name: "Vega", y: risk.points.map((p) => p.vega), line: { color: "#b388ff", width: 1.5 } },
    { name: "Rho", y: risk.points.map((p) => p.rho), line: { color: "#80cbc4", width: 1.5 } },
  ].map((t) => ({ ...t, x: spots, type: "scatter", mode: "lines" }));

  Plotly.newPlot(
    "risk-chart",
    traces,
    {
      paper_bgcolor: "#161b22",
      plot_bgcolor: "#161b22",
      font: { color: "#e6edf3" },
      margin: { t: 30, r: 20, b: 50, l: 60 },
      xaxis: { title: "قیمت BTC (USD)", gridcolor: "#30363d" },
      yaxis: { title: "مقدار", gridcolor: "#30363d" },
      legend: { orientation: "h", y: 1.12 },
      shapes: [{
        type: "line", x0: spot, x1: spot, y0: 0, y1: 1, yref: "paper",
        line: { color: "#8b949e", width: 1, dash: "dash" },
      }],
    },
    { responsive: true, displayModeBar: false }
  );

  document.getElementById("graph-subtitle").textContent =
    `Mode: ${risk.mode} | Legs: ${risk.legs_count} | جمع‌آوری خودکار`;
}

async function refresh() {
  try {
    const data = await fetchLatest();
    renderScreener(data);
    renderRiskChart(data);
  } catch (e) {
    console.error(e);
    document.getElementById("screener-body").innerHTML =
      '<tr><td colspan="9" class="muted">خطا — scheduler در حال اجراست؟</td></tr>';
  }
}

refresh();
setInterval(refresh, REFRESH_MS);
