// Whiskers chat UI: multi-conversation sidebar + word-by-word streaming over SSE.

// Each conversation keeps its own message history in the browser; the server maps
// its conversation_id to an SDK session so the agent remembers context per chat.
const conversations = new Map(); // id -> { title, messages: [{role, text}] }
let activeId = null;

const $ = (sel) => document.querySelector(sel);
const listEl = $("#conversation-list");
const messagesEl = $("#messages");
const inputEl = $("#input");
const formEl = $("#composer");
const sendBtn = $("#send");

function newConversationId() {
  return (crypto.randomUUID && crypto.randomUUID()) ||
    "c-" + Date.now() + "-" + Math.random().toString(16).slice(2);
}

function createConversation() {
  const id = newConversationId();
  conversations.set(id, { title: "New chat", messages: [] });
  activeId = id;
  renderSidebar();
  renderMessages();
  inputEl.focus();
}

function switchConversation(id) {
  activeId = id;
  renderSidebar();
  renderMessages();
}

function renderSidebar() {
  listEl.innerHTML = "";
  for (const [id, conv] of conversations) {
    const li = document.createElement("li");
    li.textContent = conv.title;
    li.className = id === activeId ? "active" : "";
    li.onclick = () => switchConversation(id);
    listEl.appendChild(li);
  }
}

function renderMessages() {
  messagesEl.innerHTML = "";
  const conv = conversations.get(activeId);
  if (!conv || conv.messages.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML =
      '<div class="paw">🐾</div><p>Hi! I\'m Whiskers. Ask me anything about your cat — ' +
      "food safety, vital signs, or general care. (I'm not a vet — call yours for anything serious.)</p>";
    messagesEl.appendChild(empty);
    return;
  }
  for (const m of conv.messages) addBubble(m.role, m.text, false);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// Render a message bubble. Bot text gets minimal markdown (**bold**, newlines).
function addBubble(role, text, animate) {
  const div = document.createElement("div");
  div.className = "msg " + (role === "user" ? "user" : "bot");
  if (role === "bot") div.innerHTML = formatBot(text);
  else div.textContent = text;
  if (animate) div.classList.add("blink");
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function formatBot(text) {
  const escaped = text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
}

function addToolNote(label) {
  const nice = { check_vitals: "checking vital signs", check_food_safety: "looking up food/plant safety" };
  const div = document.createElement("div");
  div.className = "tool-note";
  div.textContent = "🔧 " + (nice[label] || label) + "…";
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage(text) {
  const conv = conversations.get(activeId);
  conv.messages.push({ role: "user", text });
  if (conv.title === "New chat") {
    conv.title = text.slice(0, 30) + (text.length > 30 ? "…" : "");
    renderSidebar();
  }
  addBubble("user", text, false);

  const bubble = addBubble("bot", "", true);
  let acc = "";

  try {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, conversation_id: activeId }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop(); // keep incomplete trailing chunk
      for (const part of parts) {
        const line = part.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        const evt = JSON.parse(line.slice(6));
        if (evt.type === "delta") {
          acc += evt.text;
          bubble.innerHTML = formatBot(acc);
          messagesEl.scrollTop = messagesEl.scrollHeight;
        } else if (evt.type === "tool") {
          addToolNote(evt.text);
        } else if (evt.type === "final" || evt.type === "error") {
          acc = evt.text || acc;
          bubble.innerHTML = formatBot(acc);
        }
      }
    }
  } catch (err) {
    acc = "😿 Sorry, I had a little hiccup — please try again in a moment. And call your vet if it's urgent.";
    bubble.innerHTML = formatBot(acc);
  }

  bubble.classList.remove("blink");
  conv.messages.push({ role: "bot", text: acc });
}

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  sendBtn.disabled = true;
  inputEl.disabled = true;
  sendMessage(text).finally(() => {
    sendBtn.disabled = false;
    inputEl.disabled = false;
    inputEl.focus();
  });
});

$("#new-chat").addEventListener("click", createConversation);

// Boot with one empty conversation.
createConversation();
