/**
 * AITD Kanpur AI Chatbot — Self-Contained Widget
 *
 * Integration:
 *   <script src="https://aitd.ac.in/chatbot/widget.js"></script>
 *
 * Professional government institute design — navy/white color scheme.
 * Features: Markdown rendering, interactive route map, zoom overlay.
 */
(function () {
  "use strict";

  var API_URL =
    (document.currentScript && document.currentScript.getAttribute("data-api")) ||
    window.location.origin + "/api/chat";

  // Get or create unique session ID (persists within the browser tab session)
  var sessionId = null;
  try {
    sessionId = sessionStorage.getItem("aitd_chat_session_id");
    if (!sessionId) {
      sessionId = "sess_" + Math.random().toString(36).substring(2, 15) + "_" + Date.now();
      sessionStorage.setItem("aitd_chat_session_id", sessionId);
    }
  } catch (e) {
    sessionId = "sess_fallback_" + Math.random().toString(36).substring(2, 15) + "_" + Date.now();
  }

  // Get or create unique client ID (persists across browser restarts in localStorage)
  var clientId = null;
  try {
    clientId = localStorage.getItem("aitd_chat_client_id");
    if (!clientId) {
      if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        clientId = crypto.randomUUID();
      } else {
        clientId = "client_" + Math.random().toString(36).substring(2, 15) + "_" + Date.now();
      }
      localStorage.setItem("aitd_chat_client_id", clientId);
    }
  } catch (e) {
    clientId = "client_fallback_" + Math.random().toString(36).substring(2, 15) + "_" + Date.now();
  }

  // ── Google Maps URL ──
  var GMAPS_URL = "https://www.google.com/maps/place/Dr.+Ambedkar+Institute+of+Technology+for+Divyangjan/@26.5020023,80.2764365,17z";

  // ── Logo path (relative to widget directory) ──
  var LOGO_PATH = (function () {
    var script = document.currentScript;
    if (script && script.src) {
      var parts = script.src.split("/");
      parts.pop();
      return parts.join("/") + "/assets/assistant.png";
    }
    return "assets/assistant.png";
  })();

  // ── Icon path (relative to widget directory) ──
  var ICON_PATH = (function () {
    var script = document.currentScript;
    if (script && script.src) {
      var parts = script.src.split("/");
      parts.pop();
      return parts.join("/") + "/assets/assistant.png";
    }
    return "assets/assistant.png";
  })();


  // ══════════════════════════════════════════════════════════
  // CSS STYLES
  // ══════════════════════════════════════════════════════════

  var style = document.createElement("style");
  style.textContent = '\
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");\
\
#ua-toggle-container {\
  position: fixed;\
  bottom: 24px;\
  right: 24px;\
  z-index: 99999;\
  animation: ua-float 3s ease-in-out infinite;\
}\
\
#ua-toggle-btn {\
  width: 52px;\
  height: 52px;\
  border-radius: 50%;\
  border: none;\
  background: #1a365d;\
  color: #fff;\
  font-size: 26px;\
  cursor: pointer;\
  box-shadow: 0 4px 16px rgba(26,54,93,.4);\
  display: flex;\
  align-items: center;\
  justify-content: center;\
  transition: transform .25s ease, box-shadow .25s ease;\
  padding: 0;\
  overflow: hidden;\
}\
#ua-toggle-btn:hover {\
  transform: scale(1.08);\
  box-shadow: 0 6px 24px rgba(26,54,93,.55);\
}\
#ua-toggle-btn.ua-open {\
  transform: scale(1.08);\
}\
#ua-toggle-btn img { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; display: block; }\
\
@keyframes ua-float {\
  0% { transform: translateY(0); }\
  50% { transform: translateY(-8px); }\
  100% { transform: translateY(0); }\
}\
\
#ua-chat-window {\
  position: fixed;\
  bottom: 90px;\
  right: 24px;\
  width: 400px;\
  height: 560px;\
  border-radius: 16px;\
  overflow: hidden;\
  display: flex;\
  flex-direction: column;\
  z-index: 99998;\
  opacity: 0;\
  transform: translateY(16px) scale(.97);\
  pointer-events: none;\
  transition: opacity .3s ease, transform .3s ease;\
  box-shadow: 0 12px 40px rgba(0,0,0,.18), 0 0 0 1px rgba(0,0,0,.06);\
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;\
  background: #f7f8fa;\
}\
#ua-chat-window.ua-visible {\
  opacity: 1;\
  transform: translateY(0) scale(1);\
  pointer-events: auto;\
}\
\
#ua-header {\
  background: #1a365d;\
  padding: 16px 18px;\
  display: flex;\
  align-items: center;\
  gap: 12px;\
  flex-shrink: 0;\
}\
#ua-header-icon {\
  width: 38px; height: 38px; border-radius: 10px;\
  background: rgba(255,255,255,.15);\
  display: flex; align-items: center; justify-content: center;\
  font-size: 18px; color: #fff; font-weight: 700;\
}\
#ua-header-info h3 { margin:0; font-size:15px; font-weight:700; color:#fff; }\
#ua-header-info p  { margin:2px 0 0; font-size:11px; color:rgba(255,255,255,.65); }\
#ua-close-btn {\
  margin-left: auto;\
  background: rgba(255,255,255,.12);\
  border: none; border-radius: 8px;\
  width: 30px; height: 30px;\
  color: #fff; font-size: 16px;\
  cursor: pointer;\
  display: flex; align-items: center; justify-content: center;\
  transition: background .2s;\
}\
#ua-close-btn:hover { background: rgba(255,255,255,.22); }\
\
#ua-messages {\
  flex: 1;\
  overflow-y: auto;\
  padding: 16px;\
  display: flex;\
  flex-direction: column;\
  gap: 10px;\
  background: #f7f8fa;\
}\
#ua-messages::-webkit-scrollbar { width: 4px; }\
#ua-messages::-webkit-scrollbar-track { background: transparent; }\
#ua-messages::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 4px; }\
\
.ua-msg {\
  max-width: 82%;\
  padding: 10px 14px;\
  border-radius: 12px;\
  font-size: 13.5px;\
  line-height: 1.55;\
  word-wrap: break-word;\
  animation: ua-fadeIn .25s ease;\
}\
@keyframes ua-fadeIn { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }\
\
.ua-msg-user {\
  align-self: flex-end;\
  background: #1a365d;\
  color: #fff;\
  border-bottom-right-radius: 4px;\
}\
.ua-msg-bot {\
  align-self: flex-start;\
  background: #fff;\
  color: #2d3748;\
  border-bottom-left-radius: 4px;\
  border: 1px solid #e2e8f0;\
}\
.ua-msg-source {\
  margin-top: 6px;\
  padding: 5px 8px;\
  background: #edf2f7;\
  border-radius: 6px;\
  font-size: 11px;\
  color: #4a5568;\
}\
\
.ua-typing { display:flex; gap:5px; padding:10px 14px; align-self:flex-start; }\
.ua-typing span {\
  width:7px; height:7px; border-radius:50%;\
  background:#a0aec0;\
  animation: ua-bounce .6s infinite alternate;\
}\
.ua-typing span:nth-child(2) { animation-delay:.15s; }\
.ua-typing span:nth-child(3) { animation-delay:.3s; }\
@keyframes ua-bounce { to { background:#4a5568; transform:translateY(-3px); } }\
\
#ua-input-area {\
  display: flex;\
  gap: 8px;\
  padding: 12px 14px;\
  background: #fff;\
  border-top: 1px solid #e2e8f0;\
  flex-shrink: 0;\
}\
#ua-input {\
  flex: 1;\
  border: 1px solid #cbd5e0;\
  border-radius: 10px;\
  padding: 9px 14px;\
  font-size: 13.5px;\
  background: #f7f8fa;\
  color: #2d3748;\
  outline: none;\
  font-family: inherit;\
  transition: border-color .2s;\
}\
#ua-input:focus { border-color: #1a365d; }\
#ua-input::placeholder { color: #a0aec0; }\
#ua-send-btn {\
  width: 42px; height: 42px;\
  border-radius: 10px;\
  border: none;\
  background: #1a365d;\
  color: #fff;\
  cursor: pointer;\
  display: flex; align-items: center; justify-content: center;\
  transition: transform .15s, box-shadow .15s;\
  flex-shrink: 0;\
}\
#ua-send-btn:hover { transform: scale(1.05); box-shadow: 0 3px 12px rgba(26,54,93,.35); }\
#ua-send-btn svg { width:18px; height:18px; fill:#fff; }\
\
.ua-welcome {\
  text-align: center;\
  padding: 24px 16px 8px;\
  color: #718096;\
  font-size: 13px;\
  line-height: 1.6;\
}\
.ua-welcome strong { color: #1a365d; display: block; font-size: 14px; margin-bottom: 4px; }\
\
/* ── Markdown rendering ── */\
.ua-msg-bot strong { font-weight: 700; }\
.ua-msg-bot .ua-md-heading { font-weight: 700; font-size: 13px; margin: 8px 0 4px; color: #1a365d; }\
.ua-msg-bot ul { margin: 4px 0; padding-left: 18px; }\
.ua-msg-bot li { margin: 2px 0; }\
.ua-msg-bot table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 11.5px; }\
.ua-msg-bot th { background: #edf2f7; color: #1a365d; font-weight: 600; }\
.ua-msg-bot th, .ua-msg-bot td { border: 1px solid #cbd5e0; padding: 5px 8px; text-align: left; }\
\
/* ── Map card ── */\
.ua-map-card { margin-top: 10px; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; background: #fff; }\
.ua-map-card-header { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #1a365d; color: #fff; font-size: 12px; font-weight: 600; }\
.ua-map-card-header img { width: 28px; height: 28px; border-radius: 6px; background: #fff; object-fit: contain; }\
.ua-map-card-preview { cursor: pointer; display: block; width: 100%; height: 140px; background: #f7fafc; transition: opacity 0.15s; }\
.ua-map-card-preview:hover { opacity: 0.88; }\
.ua-map-card-preview svg { width: 100%; height: 100%; }\
.ua-map-card-footer { padding: 6px 12px; font-size: 11px; color: #718096; text-align: center; background: #f7f8fa; border-top: 1px solid #e2e8f0; }\
.ua-map-gmaps-btn { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 8px 12px; font-size: 12px; font-weight: 600; color: #2b6cb0; background: #ebf4ff; border: none; border-top: 1px solid #bee3f8; border-radius: 0 0 10px 10px; text-decoration: none; cursor: pointer; transition: background 0.15s; width: 100%; box-sizing: border-box; }\
.ua-map-gmaps-btn:hover { background: #dbeafe; }\
\
/* ── Map zoom overlay ── */\
#ua-map-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(26,54,93,0.97); z-index: 100; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 16px; box-sizing: border-box; opacity: 0; pointer-events: none; transition: opacity 0.2s ease; }\
#ua-map-overlay.ua-zoom-active { opacity: 1; pointer-events: auto; }\
#ua-map-overlay-close { position: absolute; top: 14px; right: 14px; background: rgba(255,255,255,0.15); border: none; border-radius: 50%; width: 34px; height: 34px; color: #fff; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s; z-index: 101; }\
#ua-map-overlay-close:hover { background: rgba(255,255,255,0.3); }\
#ua-map-overlay-title { color: #fff; font-size: 14px; font-weight: 700; margin-bottom: 12px; text-align: center; flex-shrink: 0; }\
#ua-map-overlay-svg { width: 100%; flex: 1; display: flex; align-items: center; justify-content: center; min-height: 0; }\
#ua-map-overlay-svg svg { width: 100%; height: auto; max-height: 100%; }\
#ua-map-overlay-gmaps { display: flex; align-items: center; justify-content: center; gap: 6px; margin-top: 12px; padding: 10px 20px; background: rgba(255,255,255,0.15); color: #fff; border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; font-size: 13px; font-weight: 600; text-decoration: none; transition: background 0.15s; flex-shrink: 0; }\
#ua-map-overlay-gmaps:hover { background: rgba(255,255,255,0.25); }\
\
@media (max-width: 768px) {\
  #ua-chat-window.ua-visible ~ #ua-toggle-container {\
    display: none;\
  }\
  #ua-chat-window {\
    bottom: 0 !important; right: 0 !important;\
    width: 100vw !important; height: 100vh !important;\
    border-radius: 0 !important;\
  }\
  #ua-toggle-container { bottom: 16px; right: 16px; }\
  #ua-toggle-btn { width: 46px; height: 46px; }\
}\
  ';
  document.head.appendChild(style);

  // ══════════════════════════════════════════════════════════
  // SVG ROUTE DIAGRAM (hardcoded, zero network requests)
  // ══════════════════════════════════════════════════════════

  var ROUTE_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 280" style="background:#f7fafc">'
    // Background grid
    + '<defs><pattern id="ua-grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e2e8f0" stroke-width="0.5"/></pattern></defs>'
    + '<rect width="360" height="280" fill="url(#ua-grid)"/>'
    // Title
    + '<text x="180" y="22" text-anchor="middle" font-family="Inter,sans-serif" font-size="11" font-weight="700" fill="#1a365d">AITD Kanpur — Route Guide</text>'
    // Route A: Blue path (Kanpur Central → GT Road → Rawatpur Crossing → Awadhpuri → AITD)
    + '<path d="M 55 75 C 80 75, 100 100, 130 110 C 160 120, 190 130, 210 140 C 230 150, 250 155, 275 165 C 290 172, 295 185, 290 200" fill="none" stroke="#2b6cb0" stroke-width="3" stroke-linecap="round"/>'
    // Route B: Orange path (Rawatpur → Kakadeo → Awadhpuri → AITD)
    + '<path d="M 85 195 C 110 190, 140 185, 170 190 C 200 195, 240 200, 290 200" fill="none" stroke="#ed8936" stroke-width="3" stroke-linecap="round"/>'
    // Route C: Green dashed path (Jhakarkati → GT Road → Rawatpur Crossing → AITD)
    + '<path d="M 55 145 C 80 140, 120 130, 160 130 C 200 130, 240 150, 275 165 C 285 170, 290 185, 290 200" fill="none" stroke="#38a169" stroke-width="2" stroke-dasharray="6,4" stroke-linecap="round"/>'
    // Waypoint dots
    + '<circle cx="130" cy="110" r="3" fill="#2b6cb0" opacity="0.6"/><text x="130" y="104" text-anchor="middle" font-family="Inter,sans-serif" font-size="7" fill="#4a5568">GT Road</text>'
    + '<circle cx="210" cy="140" r="3" fill="#2b6cb0" opacity="0.6"/><text x="210" y="134" text-anchor="middle" font-family="Inter,sans-serif" font-size="7" fill="#4a5568">Rawatpur Crossing</text>'
    + '<circle cx="170" cy="190" r="3" fill="#ed8936" opacity="0.6"/><text x="170" y="184" text-anchor="middle" font-family="Inter,sans-serif" font-size="7" fill="#4a5568">Kakadeo</text>'
    + '<circle cx="245" cy="175" r="3" fill="#38a169" opacity="0.6"/><text x="245" y="169" text-anchor="middle" font-family="Inter,sans-serif" font-size="7" fill="#4a5568">Awadhpuri</text>'
    // Node: Kanpur Central Railway Station (blue)
    + '<rect x="20" y="58" width="70" height="32" rx="6" fill="#2b6cb0"/>'
    + '<text x="55" y="72" text-anchor="middle" font-family="Inter,sans-serif" font-size="7" font-weight="600" fill="#fff">🚆 Kanpur</text>'
    + '<text x="55" y="82" text-anchor="middle" font-family="Inter,sans-serif" font-size="7" font-weight="600" fill="#fff">Central Stn</text>'
    // Node: Rawatpur Railway Station (blue)
    + '<rect x="50" y="182" width="70" height="28" rx="6" fill="#2b6cb0"/>'
    + '<text x="85" y="200" text-anchor="middle" font-family="Inter,sans-serif" font-size="7" font-weight="600" fill="#fff">🚆 Rawatpur Stn</text>'
    // Node: Jhakarkati Bus Stand (blue)
    + '<rect x="15" y="132" width="78" height="28" rx="6" fill="#4a7fb5"/>'
    + '<text x="54" y="150" text-anchor="middle" font-family="Inter,sans-serif" font-size="7" font-weight="600" fill="#fff">🚌 Jhakarkati Bus</text>'
    // Node: AITD Kanpur Campus (green destination)
    + '<rect x="258" y="190" width="80" height="34" rx="8" fill="#38a169" stroke="#2f855a" stroke-width="1.5"/>'
    + '<text x="298" y="205" text-anchor="middle" font-family="Inter,sans-serif" font-size="8" font-weight="700" fill="#fff">🏫 AITD</text>'
    + '<text x="298" y="216" text-anchor="middle" font-family="Inter,sans-serif" font-size="7" font-weight="600" fill="#fff">Kanpur 📍</text>'
    // Distance labels on routes
    + '<text x="100" y="95" font-family="Inter,sans-serif" font-size="7" fill="#2b6cb0" font-weight="600">~11 km</text>'
    + '<text x="145" y="210" font-family="Inter,sans-serif" font-size="7" fill="#ed8936" font-weight="600">~2.5 km</text>'
    + '<text x="105" y="145" font-family="Inter,sans-serif" font-size="7" fill="#38a169" font-weight="600">via GT Road</text>'
    // Legend
    + '<rect x="12" y="238" width="130" height="34" rx="6" fill="#fff" stroke="#e2e8f0" stroke-width="1"/>'
    + '<text x="20" y="252" font-family="Inter,sans-serif" font-size="7" font-weight="600" fill="#1a365d">Route Legend</text>'
    + '<line x1="20" y1="260" x2="35" y2="260" stroke="#2b6cb0" stroke-width="2.5"/><text x="38" y="263" font-family="Inter,sans-serif" font-size="6.5" fill="#4a5568">A: Kanpur Central</text>'
    + '<line x1="20" y1="268" x2="35" y2="268" stroke="#ed8936" stroke-width="2.5"/><text x="38" y="271" font-family="Inter,sans-serif" font-size="6.5" fill="#4a5568">B: Rawatpur Stn</text>'
    + '<line x1="85" y1="260" x2="100" y2="260" stroke="#38a169" stroke-width="2" stroke-dasharray="4,2"/><text x="103" y="263" font-family="Inter,sans-serif" font-size="6.5" fill="#4a5568">C: Jhakarkati</text>'
    + '</svg>';

  // ══════════════════════════════════════════════════════════
  // HTML STRUCTURE
  // ══════════════════════════════════════════════════════════

  // Chat window
  var chatWindow = document.createElement("div");
  chatWindow.id = "ua-chat-window";
  chatWindow.innerHTML = '\
    <div id="ua-header">\
      <div id="ua-header-icon">A</div>\
      <div id="ua-header-info">\
        <h3>AITD Kanpur Assistant</h3>\
        <p>Admissions, fees, courses, placements &amp; more</p>\
      </div>\
      <button id="ua-close-btn" aria-label="Close chat">&#10005;</button>\
    </div>\
    <div id="ua-messages">\
      <div class="ua-welcome">\
        <strong>Welcome to AITD Kanpur</strong>\
        I can help you with admissions, fees, hostel, placements, courses, faculty, and other AITD-related information.\
      </div>\
    </div>\
    <div id="ua-input-area">\
      <input id="ua-input" type="text" placeholder="Type your question..." maxlength="500" autocomplete="off" />\
      <button id="ua-send-btn" aria-label="Send message">\
        <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>\
      </button>\
    </div>\
  ';
  document.body.appendChild(chatWindow);

  // Toggle button (Appended after chatWindow for CSS sibling selector mapping)
  var toggleContainer = document.createElement("div");
  toggleContainer.id = "ua-toggle-container";
  var toggleBtn = document.createElement("button");
  toggleBtn.id = "ua-toggle-btn";
  toggleBtn.setAttribute("aria-label", "Open AITD Chatbot");
  toggleBtn.innerHTML = '<div style="font-size: 9px; font-weight: 700; line-height: 1.2; text-align: center; text-transform: uppercase; font-family: \'Inter\', sans-serif; letter-spacing: 0.3px; color: #fff; padding: 0 4px; box-sizing: border-box;">AI<br>CHATBOT</div>';
  toggleContainer.appendChild(toggleBtn);
  document.body.appendChild(toggleContainer);

  // Map zoom overlay (appended INSIDE chat window, never escapes)
  var mapOverlay = document.createElement("div");
  mapOverlay.id = "ua-map-overlay";
  mapOverlay.innerHTML = '\
    <button id="ua-map-overlay-close" aria-label="Close map">&#10005;</button>\
    <div id="ua-map-overlay-title">\xF0\x9F\x97\xBA\xEF\xB8\x8F AITD Kanpur — Route Guide</div>\
    <div id="ua-map-overlay-svg">' + ROUTE_SVG + '</div>\
    <a id="ua-map-overlay-gmaps" href="' + GMAPS_URL + '" target="_blank" rel="noopener noreferrer">\xF0\x9F\x93\x8D Open in Google Maps &rarr;</a>\
  ';
  chatWindow.appendChild(mapOverlay);

  // ══════════════════════════════════════════════════════════
  // DOM REFERENCES
  // ══════════════════════════════════════════════════════════

  var messagesDiv = document.getElementById("ua-messages");
  var inputEl = document.getElementById("ua-input");
  var sendBtn = document.getElementById("ua-send-btn");
  var closeBtn = document.getElementById("ua-close-btn");
  var mapOverlayClose = document.getElementById("ua-map-overlay-close");
  var isOpen = false;

  // ══════════════════════════════════════════════════════════
  // TOGGLE & EVENT HANDLERS
  // ══════════════════════════════════════════════════════════

  function toggleChat() {
    isOpen = !isOpen;
    chatWindow.classList.toggle("ua-visible", isOpen);
    toggleBtn.classList.toggle("ua-open", isOpen);
    if (isOpen) inputEl.focus();
  }
  toggleBtn.addEventListener("click", toggleChat);
  closeBtn.addEventListener("click", toggleChat);

  // Map overlay close
  mapOverlayClose.addEventListener("click", function () {
    mapOverlay.classList.remove("ua-zoom-active");
  });

  function openMapOverlay() {
    mapOverlay.classList.add("ua-zoom-active");
  }

  // ══════════════════════════════════════════════════════════
  // XSS-SAFE MARKDOWN PARSER
  // ══════════════════════════════════════════════════════════

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function parseMarkdown(raw) {
    // Step 1: Escape all HTML in the raw text FIRST (XSS prevention)
    var text = escapeHtml(raw);

    // Step 2: Split into lines for block-level processing
    var lines = text.split("\n");
    var html = [];
    var inTable = false;
    var inList = false;
    var tableRows = [];
    var listItems = [];
    var i, line, trimmed;

    for (i = 0; i < lines.length; i++) {
      line = lines[i];
      trimmed = line.trim();

      // Skip [MAP_ROUTE] token (handled separately in addMessage)
      if (trimmed === "[MAP_ROUTE]") {
        if (inTable) { html.push(buildTable(tableRows)); tableRows = []; inTable = false; }
        if (inList) { html.push(buildList(listItems)); listItems = []; inList = false; }
        continue;
      }

      // Table row detection: starts and ends with |
      if (trimmed.indexOf("|") === 0 && trimmed.lastIndexOf("|") === trimmed.length - 1 && trimmed.length > 2) {
        if (inList) { html.push(buildList(listItems)); listItems = []; inList = false; }
        // Skip separator rows like | :--- | :--- |
        if (/^\|[\s:*\-|]+\|$/.test(trimmed)) {
          inTable = true;
          continue;
        }
        inTable = true;
        tableRows.push(trimmed);
        continue;
      }

      // Flush table if we leave table context
      if (inTable) {
        html.push(buildTable(tableRows));
        tableRows = [];
        inTable = false;
      }

      // List items: - item, * item, or • item
      if (/^[-•*]\s+/.test(trimmed)) {
        var itemText = trimmed.replace(/^[-•*]\s+/, "");
        inList = true;
        listItems.push(inlineParse(itemText));
        continue;
      }

      // Flush list if we leave list context
      if (inList) {
        html.push(buildList(listItems));
        listItems = [];
        inList = false;
      }

      // Heading: ### text
      if (/^#{1,3}\s+/.test(trimmed)) {
        var headingText = trimmed.replace(/^#{1,3}\s+/, "");
        html.push('<div class="ua-md-heading">' + inlineParse(headingText) + "</div>");
        continue;
      }

      // Empty line → small break
      if (trimmed === "") {
        html.push("<br>");
        continue;
      }

      // Regular text line
      html.push(inlineParse(trimmed));
    }

    // Flush remaining table or list
    if (inTable) { html.push(buildTable(tableRows)); }
    if (inList) { html.push(buildList(listItems)); }

    return html.join("\n");
  }

  function inlineParse(str) {
    // Bold: **text**
    str = str.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    return str;
  }

  function buildTable(rows) {
    if (rows.length === 0) return "";
    var tableHtml = '<table>';
    var isHeader = true;
    for (var r = 0; r < rows.length; r++) {
      var cells = rows[r].split("|").filter(function (c) { return c.trim() !== ""; });
      var tag = isHeader ? "th" : "td";
      tableHtml += "<tr>";
      for (var c = 0; c < cells.length; c++) {
        tableHtml += "<" + tag + ">" + inlineParse(cells[c].trim()) + "</" + tag + ">";
      }
      tableHtml += "</tr>";
      isHeader = false;
    }
    tableHtml += "</table>";
    return tableHtml;
  }

  function buildList(items) {
    if (items.length === 0) return "";
    var listHtml = "<ul>";
    for (var j = 0; j < items.length; j++) {
      listHtml += "<li>" + items[j] + "</li>";
    }
    listHtml += "</ul>";
    return listHtml;
  }

  // ══════════════════════════════════════════════════════════
  // MAP CARD BUILDER
  // ══════════════════════════════════════════════════════════

  function buildMapCard() {
    var card = document.createElement("div");
    card.className = "ua-map-card";

    // Header with logo
    var header = document.createElement("div");
    header.className = "ua-map-card-header";
    var logoImg = document.createElement("img");
    logoImg.src = LOGO_PATH;
    logoImg.alt = "AITD Logo";
    logoImg.width = 28;
    logoImg.height = 28;
    header.appendChild(logoImg);
    var titleSpan = document.createElement("span");
    titleSpan.textContent = "\uD83D\uDDFA\uFE0F AITD Kanpur — Route Guide";
    header.appendChild(titleSpan);
    card.appendChild(header);

    // SVG preview (clickable)
    var preview = document.createElement("div");
    preview.className = "ua-map-card-preview";
    preview.innerHTML = ROUTE_SVG;
    preview.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      openMapOverlay();
    });
    card.appendChild(preview);

    // Footer hint
    var footer = document.createElement("div");
    footer.className = "ua-map-card-footer";
    footer.textContent = "\uD83D\uDD0D Click the map above to view full route diagram";
    card.appendChild(footer);

    // Google Maps button
    var gmapsBtn = document.createElement("a");
    gmapsBtn.className = "ua-map-gmaps-btn";
    gmapsBtn.href = GMAPS_URL;
    gmapsBtn.target = "_blank";
    gmapsBtn.rel = "noopener noreferrer";
    gmapsBtn.textContent = "\uD83D\uDCCD Open in Google Maps \u2192";
    card.appendChild(gmapsBtn);

    return card;
  }

  // ══════════════════════════════════════════════════════════
  // MESSAGING
  // ══════════════════════════════════════════════════════════

  function sendMessage() {
    var text = inputEl.value.trim();
    if (!text) return;

    addMessage(text, "user");
    inputEl.value = "";
    inputEl.disabled = true;
    sendBtn.disabled = true;

    showTyping();

    fetch(API_URL, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "X-Client-ID": clientId
      },
      body: JSON.stringify({ message: text, session_id: sessionId }),
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        removeTyping();
        var answer = data.answer || data.response || "Sorry, something went wrong.";
        var source = data.source || "";
        var isInstant = (data.response_type === "faq" || data.response_type === "cached" || data.response_type === "greeting" || data.response_type === "static");
        addMessage(answer, "bot", source, isInstant);
      })
      .catch(function () {
        removeTyping();
        addMessage("Connection error. Please try again later.", "bot");
      })
      .finally(function () {
        inputEl.disabled = false;
        sendBtn.disabled = false;
        inputEl.focus();
      });
  }

  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  function addMessage(text, sender, source, isInstant) {
    var el = document.createElement("div");
    el.className = "ua-msg ua-msg-" + sender;

    // Detect if response contains [MAP_ROUTE] token
    var hasMap = (sender === "bot" && text.indexOf("[MAP_ROUTE]") !== -1);

    if (sender === "bot") {
      // Add instant answer badge if applicable
      if (isInstant) {
        var noticeEl = document.createElement("div");
        noticeEl.style.fontSize = "11px";
        noticeEl.style.fontWeight = "600";
        noticeEl.style.textDecoration = "underline";
        noticeEl.style.color = "#1a365d";
        noticeEl.style.marginBottom = "4px";
        noticeEl.textContent = "\u26A1 Instant Answer";
        el.appendChild(noticeEl);
      }

      // Render markdown (bot messages only, already server-controlled text)
      var contentDiv = document.createElement("div");
      var textWithoutMapToken = text.replace(/\[MAP_ROUTE\]/g, "");
      contentDiv.innerHTML = parseMarkdown(textWithoutMapToken);
      el.appendChild(contentDiv);

      // Append map card if [MAP_ROUTE] was present
      if (hasMap) {
        el.appendChild(buildMapCard());
      }
    } else {
      // User messages: always plain text (XSS safe)
      el.textContent = text;
    }

    if (source && sender === "bot") {
      var srcEl = document.createElement("div");
      srcEl.className = "ua-msg-source";
      srcEl.textContent = "Source: " + source;
      el.appendChild(srcEl);
    }

    messagesDiv.appendChild(el);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function showTyping() {
    var el = document.createElement("div");
    el.className = "ua-typing";
    el.id = "ua-typing-indicator";
    el.innerHTML = "<span></span><span></span><span></span>";
    messagesDiv.appendChild(el);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function removeTyping() {
    var el = document.getElementById("ua-typing-indicator");
    if (el) el.remove();
  }
})();
