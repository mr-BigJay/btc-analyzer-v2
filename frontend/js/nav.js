/* Shared Persian site navigation */
(function () {
  "use strict";

  function initNav() {
    const toggle = document.getElementById("nav-toggle");
    const nav = document.getElementById("site-nav");
    if (!toggle || !nav) return;

    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });

    nav.querySelectorAll("a").forEach((a) => {
      a.addEventListener("click", () => {
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });

    const path = location.pathname.replace(/\/+$/, "") || "/";
    nav.querySelectorAll("a[data-nav]").forEach((a) => {
      const href = a.getAttribute("href") || "";
      const clean = href.replace(/\/+$/, "") || "/";
      if (clean === path || (clean !== "/" && path.endsWith(clean))) {
        a.setAttribute("aria-current", "page");
      }
    });
  }

  document.addEventListener("DOMContentLoaded", initNav);
})();
