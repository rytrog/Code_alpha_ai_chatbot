/**
 * Upload — Drag-and-drop file upload, document list, delete, rebuild index.
 */
(function () {
  "use strict";

  var API_BASE = window.location.origin + "/api";
  var dropZone  = document.getElementById("drop-zone");
  var fileInput = document.getElementById("file-input");
  var fileNameEl = document.getElementById("file-name");
  var form      = document.getElementById("upload-form");
  var statusMsg = document.getElementById("status-msg");
  var docList   = document.getElementById("doc-list");
  var rebuildBtn = document.getElementById("rebuild-btn");

  var selectedFile = null;

  dropZone.addEventListener("click", function () { fileInput.click(); });

  dropZone.addEventListener("dragover", function (e) {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", function () {
    dropZone.classList.remove("drag-over");
  });
  dropZone.addEventListener("drop", function (e) {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    if (e.dataTransfer.files.length) {
      selectedFile = e.dataTransfer.files[0];
      fileNameEl.textContent = "Selected: " + selectedFile.name;
    }
  });

  fileInput.addEventListener("change", function () {
    if (fileInput.files.length) {
      selectedFile = fileInput.files[0];
      fileNameEl.textContent = "Selected: " + selectedFile.name;
    }
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (!selectedFile) { showStatus("Please select a file.", "error"); return; }

    showStatus("Uploading and ingesting...", "loading");

    var fd = new FormData();
    fd.append("file", selectedFile);
    fd.append("source_type", document.getElementById("source-type").value);

    fetch(API_BASE + "/upload", { method: "POST", body: fd })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.error) {
          showStatus("Error: " + data.error, "error");
        } else {
          showStatus("Uploaded successfully. " + data.chunks + " chunks ingested.", "success");
          selectedFile = null;
          fileNameEl.textContent = "";
          form.reset();
          loadDocuments();
        }
      })
      .catch(function (err) {
        showStatus("Upload failed: " + err.message, "error");
      });
  });

  function loadDocuments() {
    fetch(API_BASE + "/documents")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var docs = data.documents || [];

        if (docs.length === 0) {
          docList.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;">No documents uploaded yet.</p>';
          return;
        }

        docList.innerHTML = docs.map(function (doc) {
          var date = doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : "";
          return '<div class="doc-item">' +
            '<div class="doc-icon">&#128196;</div>' +
            '<div class="doc-info">' +
              '<div class="doc-name">' + doc.filename + '</div>' +
              '<div class="doc-meta">' + doc.source_type + ' &middot; ' + doc.chunk_count + ' chunks &middot; ' + date + '</div>' +
            '</div>' +
            '<button class="btn btn-danger btn-sm" onclick="deleteDoc(' + doc.id + ')">Delete</button>' +
          '</div>';
        }).join("");
      })
      .catch(function () {
        docList.innerHTML = '<p style="color:var(--danger);font-size:13px;">Failed to load documents.</p>';
      });
  }

  window.deleteDoc = function (id) {
    if (!confirm("Delete this document?")) return;
    fetch(API_BASE + "/documents/" + id, { method: "DELETE" })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        showStatus(data.message || data.error, data.error ? "error" : "success");
        loadDocuments();
      })
      .catch(function () {
        showStatus("Delete failed.", "error");
      });
  };

  rebuildBtn.addEventListener("click", function () {
    if (!confirm("Rebuild the entire ChromaDB index? This may take a moment.")) return;
    showStatus("Rebuilding index...", "loading");
    fetch(API_BASE + "/rebuild-index", { method: "POST" })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        showStatus(data.message + " (" + data.total_chunks + " chunks)", "success");
      })
      .catch(function () {
        showStatus("Rebuild failed.", "error");
      });
  });

  function showStatus(msg, type) {
    statusMsg.textContent = msg;
    statusMsg.className = "status-msg " + type;
  }

  document.addEventListener("DOMContentLoaded", loadDocuments);
})();
