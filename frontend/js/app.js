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

function buildScenarioText(data, forecast) {
  if (!forecast) return "پیش‌بینی در دسترس نیست.";

  const price = data.price;
  const dir = forecast.direction;
  const conf = forecast.confidence;
  const support = forecast.support;
  const resistance = forecast.resistance;
  const target = forecast.primary_target;
  const invalidation = forecast.invalidation;

  const lines = [];

  if (dir === "bearish") {
    lines.push(
      `در ۴ ساعت آینده، مدل حرکت <strong class="bear">نزولی</strong> را محتمل‌تر می‌داند (اعتماد ${conf.toFixed(0)}٪).`
    );
    if (target && target < price) {
      const pct = (((target - price) / price) * 100).toFixed(1);
      lines.push(
        `مسیر محتمل: افت قیمت از ${formatPrice(price)} به سمت ${formatPrice(target)} (حدود ${pct}٪).`
      );
    } else if (support) {
      lines.push(`مسیر محتمل: فشار فروش تا حمایت ${formatPrice(support)}.`);
    }
    if (invalidation) {
      lines.push(
        `باطل‌کننده: بسته شدن و تثبیت بالای ${formatPrice(invalidation)} — سناریوی نزولی لغو می‌شود.`
      );
    }
  } else if (dir === "bullish") {
    lines.push(
      `در ۴ ساعت آینده، مدل حرکت <strong class="bull">صعودی</strong> را محتمل‌تر می‌داند (اعتماد ${conf.toFixed(0)}٪).`
    );
    if (target && target > price) {
      const pct = (((target - price) / price) * 100).toFixed(1);
      lines.push(
        `مسیر محتمل: رشد قیمت از ${formatPrice(price)} به سمت ${formatPrice(target)} (حدود +${pct}٪).`
      );
    } else if (resistance) {
      lines.push(`مسیر محتمل: صعود تا مقاومت ${formatPrice(resistance)}.`);
    }
    if (invalidation) {
      lines.push(
        `باطل‌کننده: شکست زیر ${formatPrice(invalidation)} — سناریوی صعودی لغو می‌شود.`
      );
    }
  } else {
    lines.push(
      `در ۴ ساعت آینده، بازار احتمالاً <strong class="warn">رنج</strong> می‌ماند (اعتماد ${conf.toFixed(0)}٪).`
    );
    if (support && resistance) {
      lines.push(
        `مسیر محتمل: نوسان بین ${formatPrice(support)} (کف) و ${formatPrice(resistance)} (سقف).`
      );
    }
    if (target) {
      lines.push(`هدف میانی: ${formatPrice(target)}.`);
    }
  }

  if (support || resistance) {
    const levels = [];
    if (support) levels.push(`حمایت: ${formatPrice(support)}`);
    if (resistance) levels.push(`مقاومت: ${formatPrice(resistance)}`);
    lines.push(levels.join(" · "));
  }

  return lines.join("<br>");
}

function buildVerdict(data) {
  const score = data.overall_score;
  const conf = data.overall_confidence;
  let bias = "خنثی";
  let cls = "warn";
  if (score >= 58) {
    bias = "صعودی";
    cls = "bull";
  } else if (score <= 42) {
    bias = "نزولی";
    cls = "bear";
  }
  return {
    text: `حکم کلی: بازار <strong class="${cls}">${bias}</strong> — امتیاز ${score.toFixed(0)}/100 · اعتماد ${conf.toFixed(0)}٪`,
    cls,
  };
}

function buildTechnicalBrief(data, liq, backtest, forecast) {
  const tf4h = data.timeframes["4h"];
  const tf1d = data.timeframes["1d"];
  const tf1w = data.timeframes["1w"];
  const d = data.derivatives;
  const s = data.sentiment;
  const oc = data.onchain;
  const macro = data.macro;
  const cx = data.coinex;
  const cai = data.coinex_ai;
  const lv = tf4h.levels || {};
  const verdict = buildVerdict(data);

  const mtfNote = data.mtf_aligned
    ? "هر سه تایم‌فریم هم‌جهت هستند — سیگنال قوی‌تر"
    : "تایم‌فریم‌ها ناهماهنگ — احتیاط در معامله کوتاه‌مدت";

  const factors = [];
  if (d.funding_rate != null) {
    factors.push(`فاندینگ ${(d.funding_rate * 100).toFixed(4)}٪`);
  }
  if (d.open_interest_change_pct != null) {
    factors.push(`OI ${d.open_interest_change_pct > 0 ? "+" : ""}${d.open_interest_change_pct.toFixed(2)}٪`);
  }
  if (d.long_short_ratio != null) {
    factors.push(`L/S ${d.long_short_ratio.toFixed(2)}`);
  }
  if (s.fear_greed_value != null) {
    factors.push(`F&G ${s.fear_greed_value} (${s.fear_greed_label || ""})`);
  }
  if (oc?.mvrv != null) {
    factors.push(`MVRV ${oc.mvrv}`);
  }
  if (macro?.macro_bias) {
    factors.push(`ماکرو: ${BIAS_FA[macro.macro_bias] || macro.macro_bias}`);
  }
  if (liq?.zones?.length) {
    factors.push(`لیکوئیدیشن: ${liq.zones.length} زون نزدیک قیمت`);
  }
  if (cx?.research_note) {
    factors.push(`CoinEx Futures: ${cx.bias_label} — ${cx.research_note}`);
  }
  if (cai?.summary) {
    factors.push(`CoinEx AI Research: ${cai.bias_label} — ${cai.summary}`);
  }

  const bt = backtest?.find((r) => r.timeframe === "1d") || backtest?.[0];
  let btNote = "";
  if (bt) {
    const quality = bt.profit_factor >= 1.3 && bt.win_rate >= 50 ? "قابل اتکا" : "با احتیاط";
    btNote = `بک‌تست ${bt.timeframe}: WR ${bt.win_rate}٪ · PF ${bt.profit_factor} — ${quality}`;
  }

  const SMC_FA = {
    bos_bullish: "BOS صعودی",
    bos_bearish: "BOS نزولی",
    choch_bullish: "CHoCH صعودی",
    choch_bearish: "CHoCH نزولی",
  };
  const smcLabel = SMC_FA[lv.smc_signal] || null;

  return `
    <div class="brief-report">
      <div class="brief-verdict ${verdict.cls}">${verdict.text}</div>
      <p class="brief-summary">${data.summary}</p>

      <div class="brief-section">
        <h3>وضعیت تایم‌فریم‌ها</h3>
        <table class="brief-table">
          <thead><tr><th>تایم‌فریم</th><th>روند</th><th>امتیاز</th><th>اعتماد</th></tr></thead>
          <tbody>
            <tr><td>هفتگی</td><td class="${trendClass(tf1w.trend)}">${TREND_FA[tf1w.trend]}</td><td>${tf1w.score.toFixed(0)}</td><td>${tf1w.confidence.toFixed(0)}٪</td></tr>
            <tr><td>روزانه</td><td class="${trendClass(tf1d.trend)}">${TREND_FA[tf1d.trend]}</td><td>${tf1d.score.toFixed(0)}</td><td>${tf1d.confidence.toFixed(0)}٪</td></tr>
            <tr><td>4 ساعته</td><td class="${trendClass(tf4h.trend)}">${TREND_FA[tf4h.trend]}</td><td>${tf4h.score.toFixed(0)}</td><td>${tf4h.confidence.toFixed(0)}٪</td></tr>
          </tbody>
        </table>
        <p class="brief-note">${mtfNote}</p>
      </div>

      <div class="brief-section">
        <h3>سطوح و ساختار (4h)</h3>
        <ul class="brief-list">
          ${lv.support ? `<li>حمایت: <strong>${formatPrice(lv.support)}</strong></li>` : ""}
          ${lv.resistance ? `<li>مقاومت: <strong>${formatPrice(lv.resistance)}</strong></li>` : ""}
          ${lv.fib_nearest ? `<li>فیبوناچی نزدیک: <strong>${lv.fib_nearest}</strong></li>` : ""}
          ${smcLabel ? `<li>SMC: <strong>${smcLabel}</strong></li>` : "<li>SMC: بدون شکست ساختاری معنادار</li>"}
        </ul>
      </div>

      ${
        factors.length
          ? `<div class="brief-section"><h3>فاکتورهای محیطی</h3><ul class="brief-list">${factors.map((f) => `<li>${f}</li>`).join("")}</ul></div>`
          : ""
      }

      ${
        cai
          ? `<div class="brief-section"><h3>CoinEx AI Research</h3><ul class="brief-list">
              <li>خلاصه: <strong class="${trendClass(cai.signal)}">${cai.summary}</strong></li>
              <li>کوتاه‌مدت: ${cai.short_trend || "—"}${cai.short_orientation ? ` (${cai.short_orientation})` : ""}</li>
              <li>بلندمدت: ${cai.long_trend || "—"}${cai.long_orientation ? ` (${cai.long_orientation})` : ""}</li>
              <li>${cai.core_content || cai.trend_summary || cai.research_note}</li>
            </ul></div>`
          : ""
      }

      ${
        cx
          ? `<div class="brief-section"><h3>تحقیق CoinEx Futures</h3><ul class="brief-list">
              <li>سیگنال: <strong class="${trendClass(cx.signal)}">${cx.bias_label}</strong></li>
              <li>فاندینگ: ${cx.funding_rate != null ? (cx.funding_rate * 100).toFixed(4) + "٪" : "—"} · پریمیوم: ${cx.premium_pct != null ? cx.premium_pct.toFixed(3) + "٪" : "—"}</li>
              <li>OI: ${cx.open_interest != null ? cx.open_interest.toFixed(2) + " BTC" : "—"}${cx.oi_change_pct != null ? ` (${cx.oi_change_pct >= 0 ? "+" : ""}${cx.oi_change_pct}٪)` : ""}</li>
              <li>تیکر خرید/فروش: ${cx.taker_buy_sell_ratio != null ? cx.taker_buy_sell_ratio.toFixed(2) : "—"}</li>
              <li>${cx.research_note}</li>
            </ul></div>`
          : ""
      }

      <div class="brief-section brief-scenario">
        <h3>سناریوی پیش‌رو (۴ ساعت آینده)</h3>
        <div class="brief-scenario-body">${buildScenarioText(data, forecast)}</div>
        ${forecast?.summary ? `<p class="brief-scenario-summary">${forecast.summary}</p>` : ""}
      </div>

      ${btNote ? `<p class="brief-footnote">${btNote}</p>` : ""}
      <p class="brief-disclaimer">⚠️ تحلیل است، نه توصیه سرمایه‌گذاری</p>
    </div>
  `;
}

function updateTechnicalBrief(data, liq, backtest, forecast) {
  const el = document.getElementById("tech-brief");
  if (!el) return;
  el.innerHTML = buildTechnicalBrief(data, liq, backtest, forecast);
  el.classList.remove("muted");
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

  const cx = data.coinex;
  const cai = data.coinex_ai;
  if (cx) {
    document.getElementById("coinex-funding").textContent =
      cx.funding_rate != null ? `${(cx.funding_rate * 100).toFixed(4)}%` : "—";
    document.getElementById("coinex-premium").textContent =
      cx.premium_pct != null ? `${cx.premium_pct >= 0 ? "+" : ""}${cx.premium_pct.toFixed(3)}%` : "—";
    document.getElementById("coinex-oi").textContent =
      cx.open_interest != null
        ? `${cx.open_interest.toFixed(2)} BTC${cx.oi_change_pct != null ? ` (${cx.oi_change_pct >= 0 ? "+" : ""}${cx.oi_change_pct}%)` : ""}`
        : "—";
    document.getElementById("coinex-taker").textContent =
      cx.taker_buy_sell_ratio != null ? cx.taker_buy_sell_ratio.toFixed(2) : "—";
    const sigEl = document.getElementById("coinex-signal");
    sigEl.textContent = cx.bias_label || cx.signal;
    sigEl.className = cx.signal === "bullish" ? "bull" : cx.signal === "bearish" ? "bear" : "";
  }

  if (cai) {
    document.getElementById("coinex-ai-summary").textContent = cai.summary || "—";
    document.getElementById("coinex-ai-short").textContent = cai.short_trend || "—";
    document.getElementById("coinex-ai-long").textContent = cai.long_trend || "—";
    const aiSigEl = document.getElementById("coinex-ai-signal");
    aiSigEl.textContent = cai.bias_label || cai.signal;
    aiSigEl.className = cai.signal === "bullish" ? "bull" : cai.signal === "bearish" ? "bear" : "";
    document.getElementById("coinex-ai-core").textContent =
      cai.core_content || cai.trend_summary || "—";
  }

  const tf4h = data.timeframes["4h"];
  const lv = tf4h.levels || {};
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
    updateTechnicalBrief(overview, liq, backtest, forecast);
    await loadChart(currentTf);
  } catch (e) {
    console.error(e);
    document.getElementById("updated-at").textContent = "خطا در دریافت داده";
  }
}

initChart();
refresh();
setInterval(refresh, 5 * 60 * 1000);

document.getElementById("guide-toggle")?.addEventListener("click", () => {
  const body = document.getElementById("guide-body");
  const btn = document.getElementById("guide-toggle");
  const open = body.classList.toggle("collapsed");
  btn.setAttribute("aria-expanded", String(!open));
  btn.querySelector(".guide-chevron").textContent = open ? "▸" : "▾";
});
