let currentTf = "1d";
let currentMode = "auto";
let selectedInstruments = new Set();

async function fetchScreener() {
  const minSize = document.getElementById("min-size").value;
  const res = await fetch(
    `/api/v1/options/screener?timeframe=${currentTf}&min_size=${minSize}&limit=200`
  );
  if (!res.ok) throw new Error("screener failed");
  return res.json();
}

async function fetchRiskProfile(instruments) {
  let url = `/api/v1/options/risk-profile?mode=${currentMode}&timeframe=${currentTf}`;
  if (instruments && instruments.length) {
    url += `&instruments=${encodeURIComponent(instruments.join(","))}`;
    url += "&mode=selected";
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error("risk profile failed");
  return res.json();
}

function formatUsd(n) {
  if (n == null) return "—";
  return "$" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function renderScreener(data) {
  document.getElementById("spot-price").textContent = `BTC: ${formatUsd(data.spot_current)}`;
  document.getElementById("sum-count").textContent = data.summary.position_count;
  document.getElementById("sum-size").textContent = data.summary.total_size;
  document.getElementById("sum-value").textContent = formatUsd(data.summary.total_entry_value_usd);

  const tbody = document.getElementById("screener-body");
  if (!data.rows.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="muted">داده‌ای نیست</td></tr>';
    return;
  }

  tbody.innerHTML = data.rows
    .map(
      (r) => `
    <tr data-inst="${r.instrument_name}" class="${selectedInstruments.has(r.instrument_name) ? "selected" : ""}">
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

  tbody.querySelectorAll("tr[data-inst]").forEach((row) => {
    row.addEventListener("click", () => {
      const inst = row.dataset.inst;
      if (selectedInstruments.has(inst)) {
        selectedInstruments.delete(inst);
        row.classList.remove("selected");
      } else {
        selectedInstruments.add(inst);
        row.classList.add("selected");
      }
      loadRiskGraph();
    });
  });
}

function renderRiskChart(data) {
  const modeLabels = {
    private: "🔐 Private Portfolio",
    public: "📊 Public Trades",
    selected: "✅ Selected",
    auto: "⚡ Auto",
  };
  document.getElementById("mode-badge").textContent =
    modeLabels[data.mode] || data.mode;

  if (!data.points.length) {
    document.getElementById("risk-chart").innerHTML =
      '<p class="muted" style="padding:2rem">داده‌ای برای نمودار نیست</p>';
    return;
  }

  const spots = data.points.map((p) => p.spot);
  const spot = data.spot_current;

  const traces = [
    { name: "PnL (USD)", y: data.points.map((p) => p.pnl), line: { color: "#58a6ff", width: 2.5 } },
    { name: "Delta", y: data.points.map((p) => p.delta), line: { color: "#26a69a", width: 1.5 } },
    { name: "Gamma", y: data.points.map((p) => p.gamma * 1000), line: { color: "#f0b429", width: 1.5 } },
    { name: "Theta", y: data.points.map((p) => p.theta), line: { color: "#ef5350", width: 1.5 } },
    { name: "Vega", y: data.points.map((p) => p.vega), line: { color: "#b388ff", width: 1.5 } },
    { name: "Rho", y: data.points.map((p) => p.rho), line: { color: "#80cbc4", width: 1.5 } },
  ].map((t) => ({ ...t, x: spots, type: "scatter", mode: "lines" }));

  const layout = {
    paper_bgcolor: "#161b22",
    plot_bgcolor: "#161b22",
    font: { color: "#e6edf3", family: "system-ui" },
    margin: { t: 30, r: 20, b: 50, l: 60 },
    xaxis: {
      title: "قیمت BTC (USD)",
      gridcolor: "#30363d",
      zerolinecolor: "#30363d",
    },
    yaxis: {
      title: "مقدار",
      gridcolor: "#30363d",
      zerolinecolor: "#30363d",
    },
    legend: { orientation: "h", y: 1.12, x: 0 },
    shapes: [
      {
        type: "line",
        x0: spot,
        x1: spot,
        y0: 0,
        y1: 1,
        yref: "paper",
        line: { color: "#8b949e", width: 1, dash: "dash" },
      },
    ],
    annotations: [
      {
        x: spot,
        y: 1.05,
        yref: "paper",
        text: `Spot: ${formatUsd(spot)}`,
        showarrow: false,
        font: { color: "#8b949e", size: 11 },
      },
    ],
  };

  Plotly.newPlot("risk-chart", traces, layout, { responsive: true, displayModeBar: false });

  const hint = data.deribit_configured
    ? `Mode: ${data.mode} | Legs: ${data.legs_count}`
    : `Mode: ${data.mode} | برای Private API Key در .env تنظیم کنید`;
  document.getElementById("graph-subtitle").textContent = hint;
}

async function loadScreener() {
  try {
    const data = await fetchScreener();
    renderScreener(data);
  } catch (e) {
    console.error(e);
    document.getElementById("screener-body").innerHTML =
      '<tr><td colspan="9" class="muted">خطا در دریافت داده</td></tr>';
  }
}

async function loadRiskGraph() {
  try {
    const insts = selectedInstruments.size ? [...selectedInstruments] : null;
    const data = await fetchRiskProfile(insts);
    renderRiskChart(data);
  } catch (e) {
    console.error(e);
  }
}

document.querySelectorAll(".tf-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tf-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentTf = btn.dataset.tf;
  });
});

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentMode = btn.dataset.mode;
    loadRiskGraph();
  });
});

document.getElementById("btn-fetch").addEventListener("click", async () => {
  await loadScreener();
  await loadRiskGraph();
});

document.getElementById("btn-refresh-graph").addEventListener("click", loadRiskGraph);

loadScreener().then(loadRiskGraph);
