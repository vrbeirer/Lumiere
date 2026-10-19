(function () {
  "use strict";

  const messagesArea = document.getElementById("messagesArea");
  const messageInput = document.getElementById("messageInput");
  const sendBtn      = document.getElementById("sendBtn");
  const resetBtn     = document.getElementById("resetBtn");
  const themeToggle  = document.getElementById("themeToggle");
  const widgetBtn    = document.getElementById("widgetToggleBtn");
  const widgetLabel  = document.getElementById("widgetToggleLabel");
  const chatBubble   = document.getElementById("chatBubble");

  // ── Theme ──────────────────────────────────────────────────────
  const savedTheme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);

  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
  });

  // ── Widget mode ────────────────────────────────────────────────
  let isWidget = false;
  let isCollapsed = false;

  widgetBtn.addEventListener("click", () => {
    isWidget = !isWidget;
    isCollapsed = false;

    if (isWidget) {
      document.body.classList.add("widget-mode");
      document.body.classList.remove("widget-collapsed");
      widgetLabel.textContent = "Exit Widget";
    } else {
      document.body.classList.remove("widget-mode", "widget-collapsed");
      widgetLabel.textContent = "Preview as Widget";
    }
  });

  chatBubble.addEventListener("click", () => {
    isCollapsed = !isCollapsed;
    document.body.classList.toggle("widget-collapsed", isCollapsed);
  });

  // ── Auto-resize textarea ───────────────────────────────────────
  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + "px";
  });

  // ── Send on Enter ──────────────────────────────────────────────
  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener("click", sendMessage);

  // ── Quick links ────────────────────────────────────────────────
  document.querySelectorAll(".quick-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      messageInput.value = btn.dataset.q;
      messageInput.dispatchEvent(new Event("input"));
      sendMessage();
    });
  });

  // ── Reset ──────────────────────────────────────────────────────
  resetBtn.addEventListener("click", async () => {
    try { await fetch("/api/reset", { method: "POST" }); } catch (_) {}
    messagesArea.innerHTML = "";
    appendWelcome();
  });

  // ── Core send ──────────────────────────────────────────────────
  async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || sendBtn.disabled) return;

    removeWelcome();
    appendUserMessage(text);
    messageInput.value = "";
    messageInput.style.height = "auto";
    sendBtn.disabled = true;

    const typingEl = appendTyping();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error("Network error");
      const data = await res.json();
      typingEl.remove();
      appendAssistantMessage(data.answer, data.sources || []);
    } catch (err) {
      typingEl.remove();
      appendAssistantMessage(
        "I'm having a brief technical difficulty. Please try again in a moment.",
        []
      );
    } finally {
      sendBtn.disabled = false;
      messageInput.focus();
    }
  }

  // ── DOM helpers ────────────────────────────────────────────────
  function removeWelcome() {
    const w = messagesArea.querySelector(".welcome-block");
    if (w) w.remove();
  }

  function appendWelcome() {
    const el = document.createElement("div");
    el.className = "welcome-block";
    el.innerHTML = `
      <div class="welcome-icon">✦</div>
      <h2 class="welcome-title">Good day, welcome.</h2>
      <p class="welcome-sub">I'm your personal concierge. Ask me anything about our dining, events, loyalty program, or policies — I'm here to help.</p>`;
    messagesArea.appendChild(el);
  }

  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "msg-row user";
    row.innerHTML = `
      <div class="msg-avatar">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
      </div>
      <div class="msg-body">
        <div class="msg-bubble">${escapeHtml(text)}</div>
      </div>`;
    messagesArea.appendChild(row);
    scrollBottom();
  }

  function appendTyping() {
    const row = document.createElement("div");
    row.className = "msg-row assistant";
    row.innerHTML = `
      <div class="msg-avatar">L</div>
      <div class="msg-body">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>`;
    messagesArea.appendChild(row);
    scrollBottom();
    return row;
  }

  function appendAssistantMessage(text, sources) {
    const row = document.createElement("div");
    row.className = "msg-row assistant";
    const formattedText = formatMarkdown(text);
    const sourcesHtml = buildSourcesHtml(sources);
    row.innerHTML = `
      <div class="msg-avatar">L</div>
      <div class="msg-body">
        <div class="msg-bubble">${formattedText}</div>
        ${sourcesHtml}
      </div>`;
    messagesArea.appendChild(row);
    scrollBottom();

    const toggle = row.querySelector(".sources-toggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const list = row.querySelector(".sources-list");
        toggle.classList.toggle("open");
        list.classList.toggle("visible");
      });
    }
  }

  function buildSourcesHtml(sources) {
    if (!sources || sources.length === 0) return "";
    const tags = sources.map((s) => `
      <span class="source-tag">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
        ${escapeHtml(s.source)}
      </span>`).join("");
    return `
      <div class="sources-block">
        <button class="sources-toggle">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"></polyline></svg>
          Sources (${sources.length})
        </button>
        <div class="sources-list">${tags}</div>
      </div>`;
  }

  function formatMarkdown(text) {
    return escapeHtml(text)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/^[-•]\s+(.+)$/gm, "<li>$1</li>")
      .replace(/(<li>.*<\/li>(\n|$))+/g, (m) => `<ul style="margin:8px 0 8px 16px;display:flex;flex-direction:column;gap:4px">${m}</ul>`)
      .replace(/\n/g, "<br>");
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function scrollBottom() {
    requestAnimationFrame(() => {
      messagesArea.scrollTop = messagesArea.scrollHeight;
    });
  }
})();