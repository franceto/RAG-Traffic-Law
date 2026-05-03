const form = document.getElementById("askForm")
const input = document.getElementById("question")
const chat = document.getElementById("chat")
const sendBtn = document.getElementById("sendBtn")
const clearBtn = document.getElementById("clearBtn")
const openSystemBtn = document.getElementById("openSystemBtn")
const closeSystemBtn = document.getElementById("closeSystemBtn")
const drawerOverlay = document.getElementById("drawerOverlay")
const examples = document.querySelectorAll(".example")

function scrollToBottom() {
  chat.scrollTop = chat.scrollHeight
}

function addMessage(text, role) {
  const div = document.createElement("div")
  div.className = `message ${role}`
  div.textContent = text
  chat.appendChild(div)
  scrollToBottom()
  return div
}

function openDrawer() {
  document.body.classList.add("drawer-open")
}

function closeDrawer() {
  document.body.classList.remove("drawer-open")
}

async function ask(question) {
  addMessage(question, "user")

  const loading = addMessage("Đang xử lý...", "loading")
  sendBtn.disabled = true
  sendBtn.textContent = "..."

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question})
    })

    const json = await res.json()
    loading.remove()

    if (!json.ok) {
      addMessage("Có lỗi khi xử lý câu hỏi.", "bot")
      return
    }

    const answer = json.data?.answer || "Tôi chưa có câu trả lời phù hợp."
    addMessage(answer, "bot")
  } catch (err) {
    loading.remove()
    addMessage("Không kết nối được hệ thống.", "bot")
  } finally {
    sendBtn.disabled = false
    sendBtn.textContent = "Gửi"
    input.focus()
    scrollToBottom()
  }
}

form.addEventListener("submit", e => {
  e.preventDefault()
  const question = input.value.trim()
  if (!question) return
  input.value = ""
  ask(question)
})

examples.forEach(btn => {
  btn.addEventListener("click", () => {
    ask(btn.textContent.trim())
  })
})

clearBtn.addEventListener("click", () => {
  chat.innerHTML = ""
  addMessage("Xin chào. Bạn hãy nhập câu hỏi về xử phạt giao thông.", "bot")
  input.focus()
})

openSystemBtn.addEventListener("click", openDrawer)
closeSystemBtn.addEventListener("click", closeDrawer)
drawerOverlay.addEventListener("click", closeDrawer)

document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeDrawer()
})
