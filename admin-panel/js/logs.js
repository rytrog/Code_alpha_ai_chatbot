/**
 * Logs — Paginated, filterable chat log viewer.
 */
(function () {
  "use strict";

  const API_BASE = window.location.origin + "/api";
  const logsBody   = document.getElementById("logs-body");
  const pagination = document.getElementById("pagination");
  const dateFilter  = document.getElementById("date-filter");
  const searchFilter = document.getElementById("search-filter");
  const filterBtn   = document.getElementById("filter-btn");

  let currentPage = 1;
  const perPage = 30;

  /* ── Badge HTML ── */
  function badgeFor(type) {
    var cls = {
      greeting: "badge-greeting", faq: "badge-faq", cached: "badge-cached",
      rag: "badge-rag", out_of_scope: "badge-out", error: "badge-error"
    };
    return '<span class="badge ' + (cls[type] || "badge-rag") + '">' + type + '</span>';
  }

  /* ── Load logs ── */
  async function loadLogs(page) {
    currentPage = page || 1;
    var url = API_BASE + "/logs?page=" + currentPage + "&per_page=" + perPage;
    if (searchFilter.value) url += "&search=" + encodeURIComponent(searchFilter.value);
    if (dateFilter.value) url += "&date=" + dateFilter.value;

    try {
      var res = await fetch(url);
      var data = await res.json();
      var logs = data.logs || [];

      if (logs.length === 0) {
        logsBody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:30px;color:var(--text-secondary);">No logs found.</td></tr>';
        pagination.innerHTML = "";
        return;
      }

      logsBody.innerHTML = logs.map(function (l) {
        var ts = l.created_at ? new Date(l.created_at).toLocaleString() : "—";
        var q = l.question.length > 60 ? l.question.substring(0, 60) + "…" : l.question;
        var a = l.answer.length > 80 ? l.answer.substring(0, 80) + "…" : l.answer;
        return '<tr>' +
          '<td>' + ts + '</td>' +
          '<td title="' + l.question.replace(/"/g, '&quot;') + '">' + q + '</td>' +
          '<td title="' + l.answer.replace(/"/g, '&quot;') + '">' + a + '</td>' +
          '<td>' + badgeFor(l.response_type) + '</td>' +
          '<td>' + l.response_time_ms.toFixed(0) + ' ms</td>' +
        '</tr>';
      }).join("");

      /* Pagination */
      var totalPages = data.total_pages || 1;
      var html = '<button ' + (currentPage <= 1 ? 'disabled' : '') + ' onclick="goPage(' + (currentPage - 1) + ')">← Prev</button>';
      html += '<span>Page ' + currentPage + ' / ' + totalPages + '</span>';
      html += '<button ' + (currentPage >= totalPages ? 'disabled' : '') + ' onclick="goPage(' + (currentPage + 1) + ')">Next →</button>';
      pagination.innerHTML = html;

    } catch (err) {
      logsBody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:30px;color:#f87171;">Failed to load logs.</td></tr>';
    }
  }

  window.goPage = function (p) { loadLogs(p); };

  filterBtn.addEventListener("click", function () { loadLogs(1); });
  searchFilter.addEventListener("keydown", function (e) {
    if (e.key === "Enter") loadLogs(1);
  });

  document.addEventListener("DOMContentLoaded", function () { loadLogs(1); });
})();
