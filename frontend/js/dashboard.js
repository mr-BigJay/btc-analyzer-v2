/* Dashboard client — Observe → Understand → Decide (Ch.17) */
(function () {
  "use strict";

  const REFRESH_MS = 15000;
  let viewCache = null;
  let allAlerts = [];

  const $ = (id) => document.getElementById(id);

  function toneClass(tone) {
    return tone ? `tone-${tone}` : "";
  }

  function fmt(v) {
    if (v === null || v === undefined || v === "") return "—";
    if (typeof v === "number") {
      if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
      return Number.isInteger(v) ? String(v) : v.toFixed(2);
    }
    return String(v);
  }

  function setText(id, text) {
    const el = $(id);
    if (el) el.textContent = text;
  }

  function renderHeader(h) {
    setText("hdr-asset", h.asset || "—");
    setText("hdr-tf", h.timeframe || "1h");
    setText("hdr-regime", h.market_regime || "—");
    setText("hdr-dqs", h.data_quality_score != null ? `کیفیت ${fmt(h.data_quality_score)}` : "کیفیت —");
    const conn = $("hdr-conn");
    if (conn) {
      conn.textContent = h.connection_status || "—";
      conn.dataset.tone = h.connection_tone || "blue";
    }
    const alerts = $("hdr-alerts");
    if (alerts) alerts.textContent = String(h.active_alerts_count ?? 0);
    setText("last-update", h.last_update ? `به‌روزرسانی ${h.last_update}` : "");
  }

  function renderExecutive(ex) {
    const root = $("executive");
    if (!root) return;
    const items = [
      ["سوگیری بازار", ex.market_bias, ex.market_bias_tone],
      ["اطمینان", ex.confidence_score != null ? `${fmt(ex.confidence_score)}` : "—", "blue"],
      ["سلامت (MHI)", ex.market_health_index, "blue"],
      ["استرس (MSI)", ex.market_stress_index, ex.market_stress_tone],
      ["ریسک (CRS)", ex.composite_risk_score != null ? `${fmt(ex.composite_risk_score)} · ${ex.risk_level || ""}` : ex.risk_level || "—", ex.risk_tone],
      ["سناریوی اصلی", ex.primary_scenario, "blue"],
    ];
    root.innerHTML = items
      .map(
        ([label, value, tone]) =>
          `<div class="exec-metric" data-tone="${tone || "gray"}">
            <span class="label">${label}</span>
            <span class="value" title="${fmt(value)}">${fmt(value)}</span>
          </div>`
      )
      .join("");

    const banner = $("alert-banner");
    if (banner) {
      if (ex.no_trade_zone) {
        banner.classList.remove("hidden");
        banner.textContent = "ناحیه عدم معامله فعال است — حفظ سرمایه بر موقعیت جدید اولویت دارد.";
      } else {
        banner.classList.add("hidden");
      }
    }
  }

  function renderCards(cards) {
    const root = $("domain-cards");
    if (!root) return;
    if (!cards || !cards.length) {
      root.innerHTML = `<p class="empty">هنوز داده دامنه آماده نیست — ابتدا تحلیل را اجرا کنید.</p>`;
      return;
    }
    root.innerHTML = cards
      .map((c) => {
        const metrics = (c.metrics || [])
          .map(
            (m) =>
              `<li title="${m.hint || ""}"><span class="m-label">${m.label}</span><span class="m-value">${fmt(m.value)}</span></li>`
          )
          .join("");
        return `<article class="domain-card" data-tone="${c.tone || "blue"}">
          <header><h3>${c.title}</h3><span class="pill ${toneClass(c.tone)}" aria-hidden="true">${c.tone || ""}</span></header>
          <p class="summary">${c.summary || ""}</p>
          <ul class="metric-list">${metrics}</ul>
        </article>`;
      })
      .join("");
  }

  function renderNarrative(view) {
    const n = view.narrative || {};
    const plan = view.trading_plan || {};
    setText("exec-summary", n.executive_summary || "خلاصه اجرایی در دسترس نیست.");
    setText("market-narrative", n.market_narrative || "");
    setText("risk-commentary", n.risk_commentary || "");

    const scen = $("scenarios");
    if (scen) {
      const primary = n.primary_scenario || {};
      const alts = n.alternative_scenarios || [];
      const chips = [
        { name: primary.name || primary.primary_scenario || "اصلی", probability: primary.probability, primary: true },
        ...alts.slice(0, 2).map((a) => ({ name: a.name || "جایگزین", probability: a.probability })),
      ];
      scen.innerHTML = chips
        .map(
          (s) =>
            `<div class="scenario-chip"><strong>${s.primary ? "سناریوی اصلی" : "جایگزین"}</strong>${s.name}${
              s.probability != null ? ` · ${fmt(s.probability)}%` : ""
            }</div>`
        )
        .join("");
    }

    const planEl = $("trading-plan");
    if (planEl) {
      const dir = plan.preferred_direction || "no_trade";
      planEl.innerHTML = `<div><span class="dir ${dir === "long" ? "tone-green" : dir === "short" ? "tone-red" : ""}">${dir}</span>
        <span class="muted"> · ${plan.position_sizing_guidance || "راهنمای اندازه موقعیت در انتظار است"}</span></div>
        <p class="muted" style="margin-top:0.35rem">${plan.session_notes || ""}</p>`;
    }

    const detail = $("reasoning-detail");
    if (detail) {
      detail.textContent = (view.explainability && view.explainability.question ? "" : "") +
        (n.executive_summary || "") +
        (n.risk_commentary ? `\n\nریسک: ${n.risk_commentary}` : "");
    }
  }

  function renderExplain(ex) {
    const q = $("why-title");
    const list = $("explain-list");
    if (q) q.textContent = (ex && ex.question) || "چرا این سوگیری؟";
    if (!list) return;
    const bullets = (ex && ex.bullets) || [];
    list.innerHTML = bullets
      .map(
        (b) =>
          `<li><span class="mark ${b.ok ? "ok" : "bad"}" aria-hidden="true">${b.ok ? "✓" : "✗"}</span><span>${b.text}</span></li>`
      )
      .join("");
  }

  function renderAlerts(items) {
    const root = $("alert-list");
    if (!root) return;
    if (!items.length) {
      root.innerHTML = `<p class="empty">هشدار فعالی در فیلتر فعلی نیست.</p>`;
      return;
    }
    root.innerHTML = items
      .map(
        (a) => `<article class="alert-row">
          <span class="sev ${toneClass(a.severity_tone)}">${a.severity || "—"}</span>
          <div>
            <div><strong>${a.type || "رویداد"}</strong> — ${a.summary || ""}</div>
            <div class="meta">${a.category || ""} · ${a.asset || ""} · ${a.state || ""} · ${a.timestamp || ""}</div>
          </div>
          <span class="pill">${a.state || ""}</span>
        </article>`
      )
      .join("");
  }

  function applyAlertFilters() {
    const sev = ($("filter-severity") || {}).value || "";
    const cat = ($("filter-category") || {}).value || "";
    const filtered = allAlerts.filter((a) => (!sev || a.severity === sev) && (!cat || a.category === cat));
    renderAlerts(filtered);
  }

  function renderHistorical(h) {
    const root = $("historical");
    if (!root) return;
    const conf = h.confidence_trend || [];
    const bias = h.bias_evolution || [];
    const regimes = h.regime_history || [];
    const outcomes = h.prediction_outcomes || [];

    const spark = conf
      .slice(0, 24)
      .map((p) => {
        const c = Number(p.confidence) || 0;
        const hgt = Math.max(8, Math.min(100, c));
        return `<span style="height:${hgt}%" title="${fmt(c)}"></span>`;
      })
      .join("");

    root.innerHTML = `
      <div class="hist-panel"><h3>روند اطمینان</h3><div class="spark" aria-label="نمودار اطمینان">${spark || '<p class="empty">هنوز تاریخچه‌ای نیست</p>'}</div></div>
      <div class="hist-panel"><h3>تحول سوگیری</h3><ul class="hist-list">${
        bias.slice(0, 8).map((b) => `<li><span>${b.t || ""}</span><span>${b.bias || "—"}</span></li>`).join("") || "<li class='empty'>بدون تاریخچه</li>"
      }</ul></div>
      <div class="hist-panel"><h3>تاریخچه رژیم</h3><ul class="hist-list">${
        regimes.slice(0, 8).map((r) => `<li><span>${r.t || ""}</span><span>${r.regime || "—"}</span></li>`).join("") || "<li class='empty'>بدون تاریخچه</li>"
      }</ul></div>
      <div class="hist-panel"><h3>پیش‌بینی‌های اخیر</h3><ul class="hist-list">${
        outcomes.slice(0, 8).map((o) => `<li><span>${o.market_bias || "—"}</span><span>${fmt(o.confidence)}</span></li>`).join("") || "<li class='empty'>آرشیو خالی</li>"
      }</ul></div>`;
  }

  function applyPersonalization(prefs) {
    if (!prefs) return;
    document.body.dataset.density = prefs.display_density || "comfortable";
    if (prefs.high_contrast) document.body.dataset.contrast = "high";
    else delete document.body.dataset.contrast;
    if (prefs.reduced_motion) document.documentElement.style.setProperty("scroll-behavior", "auto");
    const list = $("asset-list");
    if (list && prefs.favorite_assets) {
      list.innerHTML = prefs.favorite_assets.map((a) => `<option value="${a}"></option>`).join("");
    }
  }

  function render(view) {
    viewCache = view;
    document.body.dataset.state = view.state || "Loading";
    renderHeader(view.header || {});
    renderExecutive(view.executive || {});
    renderCards(view.domain_cards || []);
    renderNarrative(view);
    renderExplain(view.explainability || {});
    allAlerts = (view.alerts && view.alerts.items) || [];
    applyAlertFilters();
    renderHistorical(view.historical || {});
    applyPersonalization(view.personalization);
    setText(
      "footer-state",
      `${view.state || "—"} · schema ${view.schema_version || "—"} · ${view.generated_at || ""}`
    );
  }

  async function loadView() {
    try {
      const res = await fetch("/api/v1/dashboard/view");
      const body = await res.json();
      const data = body.data || body;
      render(data);
    } catch (err) {
      document.body.dataset.state = "Offline";
      setText("footer-state", "آفلاین — ارتباط با API داشبورد برقرار نشد");
      setText("hdr-conn", "آفلاین");
      const conn = $("hdr-conn");
      if (conn) conn.dataset.tone = "red";
    }
  }

  function wire() {
    $("hdr-alerts")?.addEventListener("click", () => {
      document.getElementById("alerts")?.scrollIntoView({ behavior: "smooth" });
    });
    $("toggle-reasoning")?.addEventListener("click", () => {
      const detail = $("reasoning-detail");
      const btn = $("toggle-reasoning");
      if (!detail || !btn) return;
      const open = detail.classList.toggle("hidden") === false;
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.textContent = open ? "جمع‌کردن استدلال" : "نمایش استدلال";
    });
    $("filter-severity")?.addEventListener("change", applyAlertFilters);
    $("filter-category")?.addEventListener("change", applyAlertFilters);

    // Keyboard shortcuts (desktop)
    let pending = "";
    window.addEventListener("keydown", (e) => {
      if (e.target && ["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName)) return;
      if (e.key === "/") {
        e.preventDefault();
        $("asset-search")?.focus();
        return;
      }
      if (e.key === "g") {
        pending = "g";
        return;
      }
      if (pending === "g") {
        const map = { o: "overview", a: "alerts", n: "narrative", r: "intelligence" };
        const id = map[e.key];
        if (id) document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
        pending = "";
      }
    });
  }

  wire();
  loadView();
  setInterval(loadView, REFRESH_MS);
})();
