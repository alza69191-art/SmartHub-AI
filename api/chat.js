const API_BASE_URL = (window.SMART_HUB_API_URL || "").replace(/\/$/, "");
const chatForm = document.getElementById("aiChatForm");
const chatInput = document.getElementById("aiChatInput");
const chatMessages = document.getElementById("aiChatMessages");
const chatStatus = document.getElementById("aiChatStatus");
const chatHistory = [];

function addChatMessage(role, content) {
  const row = document.createElement("div");
  row.className = "chat-message " + role;
  const label = document.createElement("strong");
  label.textContent = role === "user" ? "أنت" : "SmartHub AI";
  const body = document.createElement("p");
  body.textContent = content;
  row.append(label, body);
  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;
  if (!API_BASE_URL) {
    chatStatus.textContent = "الخادم لم يُربط بعد. بعد نشر Render سنضيف رابط الخدمة هنا.";
    return;
  }

  addChatMessage("user", message);
  chatHistory.push({ role: "user", content: message });
  chatInput.value = "";
  chatStatus.textContent = "جاري التفكير...";
  const submit = chatForm.querySelector("button");
  submit.disabled = true;

  try {
    const response = await fetch(API_BASE_URL + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: chatHistory.slice(0, -1) })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "تعذر الاتصال بالخادم");
    const reply = data.reply || "لم يصل رد.";
    addChatMessage("assistant", reply);
    chatHistory.push({ role: "assistant", content: reply });
    chatStatus.textContent = "متصل";
  } catch (error) {
    chatStatus.textContent = "خطأ: " + error.message;
  } finally {
    submit.disabled = false;
    chatInput.focus();
  }
});
