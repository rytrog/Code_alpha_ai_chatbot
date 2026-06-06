/**
 * AITD Kanpur AI Chatbot — Self-Contained Widget
 *
 * Integration:
 *   <script src="https://aitd.ac.in/chatbot/widget.js"></script>
 *
 * Professional government institute design — navy/white color scheme.
 */
(function () {
  "use strict";

  var API_URL =
    (document.currentScript && document.currentScript.getAttribute("data-api")) ||
    window.location.origin + "/api/chat";

  var style = document.createElement("style");
  style.textContent = '\
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");\
\
#ua-toggle-btn {\
  position: fixed;\
  bottom: 24px;\
  right: 24px;\
  width: 58px;\
  height: 58px;\
  border-radius: 50%;\
  border: none;\
  background: #1a365d;\
  color: #fff;\
  font-size: 26px;\
  cursor: pointer;\
  z-index: 99999;\
  box-shadow: 0 4px 16px rgba(26,54,93,.4);\
  display: flex;\
  align-items: center;\
  justify-content: center;\
  transition: transform .25s ease, box-shadow .25s ease;\
}\
#ua-toggle-btn:hover {\
  transform: scale(1.08);\
  box-shadow: 0 6px 24px rgba(26,54,93,.55);\
}\
#ua-toggle-btn.ua-open {\
  transform: rotate(90deg) scale(1.08);\
}\
#ua-toggle-btn svg { width: 26px; height: 26px; fill: #fff; }\
\
#ua-chat-window {\
  position: fixed;\
  bottom: 96px;\
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
@media (max-width: 768px) {\
  #ua-chat-window {\
    bottom: 0 !important; right: 0 !important;\
    width: 100vw !important; height: 100vh !important;\
    border-radius: 0 !important;\
  }\
  #ua-toggle-btn { bottom: 16px; right: 16px; width: 52px; height: 52px; }\
}\
  ';
  document.head.appendChild(style);

  // Toggle button
  var toggleBtn = document.createElement("button");
  toggleBtn.id = "ua-toggle-btn";
  toggleBtn.setAttribute("aria-label", "Open AITD Chatbot");
  toggleBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/><path d="M7 9h2v2H7zm4 0h2v2h-2zm4 0h2v2h-2z"/></svg>';
  document.body.appendChild(toggleBtn);

  // Chat window
  var chatWindow = document.createElement("div");
  chatWindow.id = "ua-chat-window";
  chatWindow.innerHTML = '\
    <div id="ua-header">\
      <div id="ua-header-icon">A</div>\
      <div id="ua-header-info">\
        <h3>AITD Kanpur Assistant</h3>\
        <p>Admissions, fees, courses, placements & more</p>\
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

  var messagesDiv = document.getElementById("ua-messages");
  var inputEl = document.getElementById("ua-input");
  var sendBtn = document.getElementById("ua-send-btn");
  var closeBtn = document.getElementById("ua-close-btn");
  var isOpen = false;

  function toggleChat() {
    isOpen = !isOpen;
    chatWindow.classList.toggle("ua-visible", isOpen);
    toggleBtn.classList.toggle("ua-open", isOpen);
    if (isOpen) inputEl.focus();
  }
  toggleBtn.addEventListener("click", toggleChat);
  closeBtn.addEventListener("click", toggleChat);

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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        removeTyping();
        var answer = data.answer || data.response || "Sorry, something went wrong.";
        var source = data.source || "";
        var isInstant = (data.response_type === "faq" || data.response_type === "cached" || data.response_type === "greeting");
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

    if (isInstant && sender === "bot") {
      var noticeEl = document.createElement("div");
      noticeEl.style.fontSize = "11px";
      noticeEl.style.fontWeight = "600";
      noticeEl.style.textDecoration = "underline";
      noticeEl.style.color = "#1a365d";
      noticeEl.style.marginBottom = "4px";
      noticeEl.textContent = "⚡ Instant Answer";
      el.appendChild(noticeEl);
      
      var textEl = document.createElement("span");
      textEl.textContent = text;
      el.appendChild(textEl);
    } else {
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
