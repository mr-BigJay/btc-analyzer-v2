/* Persian admin console client */
(function () {
  "use strict";

  const TOKEN_KEY = "btc_admin_token";
  let token = localStorage.getItem(TOKEN_KEY) || "";
  let configCache = null;

  const $ = (id) => document.getElementById(id);

  function toast(msg, err) {
    const el = $("toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    el.classList.toggle("err", !!err);
  }

  async function api(path, opts = {}) {
    const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    if (token) headers["X-Admin-Token"] = token;
    const res = await fetch("/api/v1/admin" + path, {
      method: opts.method || "GET",
      headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      cache: "no-store",
    });
    const body = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, body };
  }

  function showAuth(mode) {
    $("auth-gate").classList.remove("hidden");
    $("admin-app").classList.add("hidden");
    $("bootstrap-box").classList.toggle("hidden", mode !== "bootstrap");
    $("login-box").classList.toggle("hidden", mode !== "login");
  }

  function showApp() {
    $("auth-gate").classList.add("hidden");
    $("admin-app").classList.remove("hidden");
  }

  function setToken(t) {
    token = t || "";
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  }

  async function refreshStatus() {
    const st = await api("/status");
    const data = (st.body && st.body.data) || {};
    $("st-version").textContent = data.version || "—";
    const health = data.health || {};
    $("st-health").textContent = health.status || (st.ok ? "ok" : "خطا");
    $("st-health").className = "value " + (health.ok ? "ok" : "warn");
    renderProgress(data.progress || (await api("/progress")).body.data);
    return data;
  }

  function renderProgress(progress) {
    const root = $("progress-list");
    if (!root || !progress) return;
    const steps = progress.steps || [];
    root.innerHTML = steps
      .map((s) => {
        const badge = s.done
          ? '<span class="badge ok">انجام شد</span>'
          : '<span class="badge wait">باقی‌مانده</span>';
        const skip =
          s.optional && !s.done
            ? `<button type="button" class="btn btn-ghost" data-skip="${s.id}">رد کردن</button>`
            : "";
        return `<div class="progress-item">
          <div class="step-num">${s.done ? "✓" : "•"}</div>
          <div><strong>${s.title}</strong><div class="hint" style="margin:0">${s.description}${s.optional ? " (اختیاری)" : ""}</div></div>
          <div>${badge}${skip}</div>
        </div>`;
      })
      .join("");
    root.querySelectorAll("[data-skip]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const r = await api("/skip/" + btn.getAttribute("data-skip"), { method: "POST" });
        if (!r.ok) return toast((r.body.error && r.body.error.message) || "خطا", true);
        toast("مرحله رد شد");
        refreshStatus();
      });
    });
    const bar = $("progress-summary");
    if (bar) bar.textContent = `${progress.completed || 0} از ${progress.total || 0} مرحله`;
  }

  function renderConfig(cfg) {
    configCache = cfg;
    const root = $("config-groups");
    if (!root) return;
    root.innerHTML = (cfg.groups || [])
      .map((g) => {
        const fields = (g.fields || [])
          .map((f) => {
            if (f.type === "bool") {
              const checked = f.value === true || f.value === "true" ? "checked" : "";
              return `<div class="field check-row">
                <input type="checkbox" id="f-${f.key}" data-key="${f.key}" data-type="bool" ${checked}/>
                <label for="f-${f.key}">${f.label}</label>
              </div>`;
            }
            const typ = f.type === "secret" ? "password" : f.type === "int" || f.type === "float" ? "number" : "text";
            const val = f.type === "secret" ? "" : f.value == null ? "" : String(f.value);
            const ph = f.type === "secret" ? (f.has_value ? "•••• (برای تغییر مقدار جدید وارد کنید)" : "") : "";
            return `<div class="field">
              <label for="f-${f.key}">${f.label}</label>
              <input id="f-${f.key}" data-key="${f.key}" data-type="${f.type}" type="${typ}" value="${val.replace(/"/g, "&quot;")}" placeholder="${ph}"/>
            </div>`;
          })
          .join("");
        return `<section style="margin-bottom:1.25rem">
          <h3 style="margin-bottom:0.75rem;color:var(--sky)">${g.title}</h3>
          <div class="field-grid">${fields}</div>
        </section>`;
      })
      .join("");
  }

  async function loadConfig() {
    const r = await api("/config");
    if (r.status === 401 || r.status === 403) {
      setToken("");
      await boot();
      return;
    }
    if (!r.ok) {
      toast((r.body.error && r.body.error.message) || "بارگذاری تنظیمات ناموفق", true);
      return;
    }
    renderConfig(r.body.data);
  }

  async function saveConfig() {
    const values = {};
    document.querySelectorAll("[data-key]").forEach((el) => {
      const key = el.getAttribute("data-key");
      const type = el.getAttribute("data-type");
      if (type === "bool") values[key] = el.checked;
      else if (type === "secret" && !el.value) return;
      else if (type === "int") values[key] = el.value === "" ? undefined : Number(el.value);
      else if (type === "float") values[key] = el.value === "" ? undefined : Number(el.value);
      else values[key] = el.value;
    });
    Object.keys(values).forEach((k) => values[k] === undefined && delete values[k]);
    const r = await api("/config", { method: "PUT", body: { values } });
    if (!r.ok) return toast((r.body.error && r.body.error.message) || "ذخیره ناموفق", true);
    toast("تنظیمات ذخیره و اعمال شد");
    renderConfig(r.body.data.config);
    refreshStatus();
  }

  async function runOp(op) {
    toast("در حال اجرا: " + op + " …");
    const r = await api("/ops/" + op, { method: "POST" });
    const data = (r.body && r.body.data) || {};
    if (!r.ok || data.ok === false) {
      toast((data.error || (r.body.error && r.body.error.message) || "عملیات ناموفق"), true);
      return;
    }
    toast("انجام شد:\n" + JSON.stringify(data, null, 2));
    refreshStatus();
  }

  function wireTabs() {
    document.querySelectorAll("[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("[data-tab]").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".admin-panel").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        const id = btn.getAttribute("data-tab");
        $(id)?.classList.add("active");
        if (id === "panel-config") loadConfig();
        if (id === "panel-setup" || id === "panel-status") refreshStatus();
      });
    });
  }

  async function boot() {
    const st = await api("/status");
    const data = (st.body && st.body.data) || {};
    if (!data.setup_complete) {
      showAuth("bootstrap");
      return;
    }
    if (!token) {
      showAuth("login");
      return;
    }
    // validate token by fetching config
    const cfg = await api("/config");
    if (!cfg.ok) {
      setToken("");
      showAuth("login");
      return;
    }
    showApp();
    renderConfig(cfg.body.data);
    refreshStatus();
  }

  function wireAuth() {
    $("btn-bootstrap")?.addEventListener("click", async () => {
      const password = $("boot-pass").value;
      const jwt = $("boot-jwt").value;
      const domain = $("boot-domain").value;
      const config = {};
      if (jwt) config.api_jwt_secret = jwt;
      if (domain) config.domain = domain;
      config.api_auth_enabled = $("boot-auth").checked;
      const r = await api("/bootstrap", { method: "POST", body: { password, config } });
      if (!r.ok) return toast((r.body.error && r.body.error.message) || "راه‌اندازی ناموفق", true);
      setToken(r.body.data.token);
      toast("راه‌اندازی اولیه انجام شد");
      showApp();
      loadConfig();
      refreshStatus();
    });
    $("btn-login")?.addEventListener("click", async () => {
      const password = $("login-pass").value;
      const r = await api("/login", { method: "POST", body: { password } });
      if (!r.ok) return toast((r.body.error && r.body.error.message) || "ورود ناموفق", true);
      setToken(r.body.data.token);
      showApp();
      loadConfig();
      refreshStatus();
    });
    $("btn-logout")?.addEventListener("click", async () => {
      await api("/logout", { method: "POST" });
      setToken("");
      showAuth("login");
    });
  }

  function wireOps() {
    $("btn-save-config")?.addEventListener("click", saveConfig);
    document.querySelectorAll("[data-op]").forEach((btn) => {
      btn.addEventListener("click", () => runOp(btn.getAttribute("data-op")));
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireTabs();
    wireAuth();
    wireOps();
    boot();
  });
})();
