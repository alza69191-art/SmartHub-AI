(() => {
  const API = (window.SMART_HUB_API_URL || "").replace(/\/$/, "");
  const $ = id => document.getElementById(id);
  const input = $("aiChatInput"), host = $("aiChatMessages"), send = $("sendChat");
  const KEY = "smarthub-chat-v1";
  let history = [];
  try {
    history = JSON.parse(localStorage.getItem(KEY) || "[]");
    if (!Array.isArray(history)) history = [];
  } catch (_) { history = []; }

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(history.slice(-40))); } catch (_) {}
  }
  function scroll() { host.scrollTop = host.scrollHeight; }
  function add(role, content, provider) {
    const row = document.createElement("article");
    row.className = "minimal-message " + (role === "user" ? "user" : "assistant");
    const label = document.createElement("div");
    label.className = "minimal-label";
    label.textContent = role === "user" ? "أنت" : (provider ? "SmartHub AI · " + provider : "SmartHub AI");
    const body = document.createElement("p");
    body.textContent = content;
    row.append(label, body);
    host.append(row);
    scroll();
    return row;
  }
  function render() {
    host.replaceChildren();
    history.forEach(item => add(item.role, item.content, item.provider));
  }
  function setBusy(busy) {
    send.disabled = busy;
    input.disabled = busy;
    send.textContent = busy ? "…" : "↑";
  }
  async function submit(value) {
    const message = (value ?? input.value).trim();
    if (!message || send.disabled) return;
    if (!API) {
      add("assistant", "رابط الخادم غير مضبوط في config.js.");
      return;
    }
    history.push({ role: "user", content: message });
    add("user", message);
    save();
    input.value = "";
    input.style.height = "auto";
    setBusy(true);
    const waiting = add("assistant", "جارٍ التفكير...");
    waiting.classList.add("typing");
    try {
      const response = await fetch(API + "/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history: history.slice(0, -1).slice(-10) })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "تعذر الحصول على رد");
      const reply = data.reply || "لم يصل رد من المساعد.";
      waiting.remove();
      history.push({ role: "assistant", content: reply, provider: data.provider || "" });
      add("assistant", reply, data.provider || "");
      save();
    } catch (error) {
      waiting.remove();
      history.pop();
      save();
      add("assistant", "تعذر الاتصال بالمساعد: " + error.message);
    } finally {
      setBusy(false);
      input.focus();
    }
  }
  send.addEventListener("click", () => submit());
  input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 180) + "px";
  });
  render();
})();