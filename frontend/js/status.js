/* Status page probes */
(function () {
  "use strict";

  function set(id, text, cls) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.className = "value" + (cls ? " " + cls : "");
  }

  async function probe(path) {
    const res = await fetch(path, { cache: "no-store" });
    const body = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, body };
  }

  async function refresh() {
    try {
      const live = await probe("/live");
      set("st-live", live.ok ? "فعال" : "خطا", live.ok ? "ok" : "bad");

      const ready = await probe("/ready");
      set("st-ready", ready.ok ? "آماده" : "ن آماده", ready.ok ? "ok" : "warn");

      const health = await probe("/health");
      const data = (health.body && health.body.data) || {};
      set("st-health", health.ok ? data.status || "ok" : "degraded", health.ok ? "ok" : "warn");
      set("st-env", data.environment || "—");
      set("st-chapter", data.chapter || "—");
      set("st-version", data.version || "—");
      const detail = document.getElementById("st-detail");
      if (detail) {
        detail.textContent = health.ok
          ? "سرویس پاسخ می‌دهد. برای جزئیات استقرار از /api/v1/deploy/status استفاده کنید."
          : "یکی از وابستگی‌ها (مثل پایگاه‌داده) آماده نیست.";
      }
    } catch (err) {
      set("st-live", "آفلاین", "bad");
      set("st-ready", "آفلاین", "bad");
      set("st-health", "آفلاین", "bad");
      const detail = document.getElementById("st-detail");
      if (detail) detail.textContent = "ارتباط با API برقرار نشد. سرویس‌ها را با docker compose ps بررسی کنید.";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    refresh();
    setInterval(refresh, 15000);
  });
})();
