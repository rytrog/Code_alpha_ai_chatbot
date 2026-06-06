/**
 * Dashboard — Fetches analytics and populates stat cards.
 */
(function () {
  "use strict";

  const API_BASE = window.location.origin + "/api";

  async function loadAnalytics() {
    try {
      const res = await fetch(API_BASE + "/analytics");
      if (!res.ok) throw new Error("API error");
      const d = await res.json();

      setText("stat-total", d.total_questions);
      setText("stat-cache", d.cache_hits);
      setText("stat-ai",    d.ai_calls);
      setText("stat-docs",  d.documents_uploaded);
      setText("stat-faq",   d.faq_hits);
      setText("stat-greet", d.greeting_hits);
      setText("stat-oos",   d.out_of_scope);
      setText("stat-time",  d.avg_response_time_ms.toFixed(0) + " ms");

      animateCounters();
    } catch (err) {
      console.error("Dashboard load error:", err);
    }
  }

  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  /* Animate counters from 0 to value */
  function animateCounters() {
    document.querySelectorAll(".stat-value").forEach(function (el) {
      const text = el.textContent;
      const num = parseInt(text, 10);
      if (isNaN(num) || num === 0) return;

      const suffix = text.replace(String(num), "");
      let current = 0;
      const step = Math.max(1, Math.floor(num / 30));
      const interval = setInterval(function () {
        current += step;
        if (current >= num) {
          current = num;
          clearInterval(interval);
        }
        el.textContent = current + suffix;
      }, 25);
    });
  }

  document.addEventListener("DOMContentLoaded", loadAnalytics);

  /* Auto-refresh every 30 seconds */
  setInterval(loadAnalytics, 30000);
})();
