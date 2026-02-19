(function () {
  "use strict";

  const messagesEl = document.getElementById("chatMessages");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const typingEl = document.getElementById("typingIndicator");
  const sessionListEl = document.getElementById("sessionList");
  const newChatBtn = document.getElementById("newChatBtn");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("chatSidebar");
  const micBtn = document.getElementById("micBtn");
  const audioPreview = document.getElementById("audioPreview");
  const audioPlayback = document.getElementById("audioPlayback");
  const discardAudioBtn = document.getElementById("discardAudioBtn");

  let chatHistory = [];
  let currentSessionId = null;

  // ── Audio recording state ──
  var mediaRecorder = null;
  var audioChunks = [];
  var pendingAudioBlob = null;
  var recordingTimer = null;
  var recordingSeconds = 0;

  // ── Markdown-lite renderer ──
  function renderMarkdown(text) {
    let html = text
      .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre><code>$2</code></pre>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(
        /\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" target="_blank">$1</a>'
      )
      .replace(/\n/g, "<br>");

    html = html.replace(/((?:<br>)?- .+(?:<br>|$))+/g, function (match) {
      var items = match
        .split("<br>")
        .filter(function (l) {
          return l.trim().startsWith("- ");
        })
        .map(function (l) {
          return "<li>" + l.trim().substring(2) + "</li>";
        })
        .join("");
      return "<ul>" + items + "</ul>";
    });

    return html;
  }

  // ── UI helpers ──
  function addMessage(role, html) {
    var div = document.createElement("div");
    div.className = "chat-message " + role;
    div.innerHTML = '<div class="message-bubble">' + html + "</div>";
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function showTyping(show) {
    typingEl.style.display = show ? "flex" : "none";
    if (show) messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setEnabled(enabled) {
    input.disabled = !enabled;
    sendBtn.disabled = !enabled;
  }

  function clearMessages() {
    messagesEl.innerHTML = "";
  }

  function showWelcome() {
    clearMessages();
    addMessage(
      "assistant",
      "Hi! I'm your ASR research assistant. I can help you:" +
        "<ul>" +
        "<li>Search and summarize recent papers</li>" +
        "<li>View the ASR leaderboard and model catalog</li>" +
        "<li>Generate daily reports, podcasts, and mindmaps</li>" +
        "<li>Create deep-dive episodes for specific papers</li>" +
        "<li>Save and manage your research notes</li>" +
        "</ul>" +
        "What would you like to know?"
    );
  }

  // ── Session management ──
  async function loadSessionList() {
    try {
      var res = await fetch("/api/chat/sessions");
      var data = await res.json();
      renderSessionList(data.sessions || []);
    } catch (e) {
      console.error("Failed to load sessions", e);
    }
  }

  function renderSessionList(sessions) {
    sessionListEl.innerHTML = "";
    sessions.forEach(function (s) {
      var item = document.createElement("div");
      item.className = "session-item" + (s.id === currentSessionId ? " active" : "");
      item.dataset.id = s.id;

      var title = document.createElement("span");
      title.className = "session-title";
      title.textContent = s.title;

      var delBtn = document.createElement("button");
      delBtn.className = "session-delete";
      delBtn.innerHTML = "&times;";
      delBtn.title = "Delete";
      delBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        deleteSession(s.id);
      });

      item.appendChild(title);
      item.appendChild(delBtn);
      item.addEventListener("click", function () {
        loadSession(s.id);
      });
      sessionListEl.appendChild(item);
    });
  }

  async function createSession() {
    try {
      var res = await fetch("/api/chat/sessions", { method: "POST" });
      var session = await res.json();
      currentSessionId = session.id;
      chatHistory = [];
      showWelcome();
      await loadSessionList();
      input.focus();
    } catch (e) {
      console.error("Failed to create session", e);
    }
  }

  async function loadSession(sessionId) {
    try {
      var res = await fetch("/api/chat/sessions/" + sessionId);
      if (!res.ok) return;
      var session = await res.json();
      currentSessionId = session.id;
      chatHistory = session.messages || [];
      clearMessages();

      if (chatHistory.length === 0) {
        showWelcome();
      } else {
        chatHistory.forEach(function (msg) {
          var role = msg.role === "model" ? "assistant" : msg.role;
          if (msg.parts && msg.parts[0] && msg.parts[0].text) {
            addMessage(role, renderMarkdown(msg.parts[0].text));
          }
        });
      }
      await loadSessionList();
      input.focus();
    } catch (e) {
      console.error("Failed to load session", e);
    }
  }

  async function saveSession(title) {
    if (!currentSessionId) return;
    try {
      var body = { messages: chatHistory };
      if (title) body.title = title;
      await fetch("/api/chat/sessions/" + currentSessionId, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      await loadSessionList();
    } catch (e) {
      console.error("Failed to save session", e);
    }
  }

  async function deleteSession(sessionId) {
    try {
      await fetch("/api/chat/sessions/" + sessionId, { method: "DELETE" });
      if (sessionId === currentSessionId) {
        currentSessionId = null;
        chatHistory = [];
        showWelcome();
      }
      await loadSessionList();
    } catch (e) {
      console.error("Failed to delete session", e);
    }
  }

  // ── Sidebar toggle ──
  sidebarToggle.addEventListener("click", function () {
    sidebar.classList.toggle("open");
  });

  // ── New chat ──
  newChatBtn.addEventListener("click", function () {
    createSession();
  });

  // ── Progress display ──
  var progressEl = null;

  function showProgress() {
    if (progressEl) return;
    progressEl = document.createElement("div");
    progressEl.className = "chat-progress";
    messagesEl.appendChild(progressEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addProgressStep(label, status) {
    if (!progressEl) showProgress();
    // Check if step already exists (update from "running" to "done")
    var existing = progressEl.querySelector('[data-tool="' + label + '"]');
    if (existing) {
      existing.className = "progress-step " + status;
      existing.querySelector(".step-icon").textContent = status === "done" ? "\u2713" : "\u00B7\u00B7\u00B7";
      messagesEl.scrollTop = messagesEl.scrollHeight;
      return;
    }
    var step = document.createElement("div");
    step.className = "progress-step " + status;
    step.dataset.tool = label;
    var icon = status === "running" ? "\u00B7\u00B7\u00B7" : "\u2713";
    step.innerHTML = '<span class="step-icon">' + icon + '</span><span class="step-label">' + label + "</span>";
    progressEl.appendChild(step);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function clearProgress() {
    if (progressEl) {
      progressEl.remove();
      progressEl = null;
    }
  }

  // ── SSE stream reader ──
  async function readStream(response) {
    var reader = response.body.getReader();
    var decoder = new TextDecoder();
    var buffer = "";
    var result = null;

    while (true) {
      var chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });

      var lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (!line.startsWith("data: ")) continue;
        try {
          var event = JSON.parse(line.substring(6));
          if (event.type === "thinking") {
            addProgressStep(event.message, "running");
          } else if (event.type === "tool_start") {
            addProgressStep(event.label, "running");
          } else if (event.type === "tool_done") {
            addProgressStep(event.label, "done");
          } else if (event.type === "substep") {
            addProgressStep(event.label, "running");
          } else if (event.type === "reply") {
            result = event;
          } else if (event.type === "error") {
            result = { error: event.message };
          }
        } catch (e) {
          // skip malformed lines
        }
      }
    }
    return result;
  }

  // ── Audio recording ──
  function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert("Microphone access requires HTTPS. Please access the site via https://.");
      return;
    }
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      audioChunks = [];
      mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      mediaRecorder.addEventListener("dataavailable", function (e) {
        if (e.data.size > 0) audioChunks.push(e.data);
      });
      mediaRecorder.addEventListener("stop", function () {
        stream.getTracks().forEach(function (t) { t.stop(); });
        pendingAudioBlob = new Blob(audioChunks, { type: "audio/webm" });
        audioPlayback.src = URL.createObjectURL(pendingAudioBlob);
        audioPreview.style.display = "flex";
        clearInterval(recordingTimer);
        recordingSeconds = 0;
        micBtn.classList.remove("recording");
        micBtn.querySelector(".mic-icon").style.display = "";
        micBtn.querySelector(".stop-icon").style.display = "none";
        micBtn.title = "Record audio";
      });
      mediaRecorder.start();
      micBtn.classList.add("recording");
      micBtn.querySelector(".mic-icon").style.display = "none";
      micBtn.querySelector(".stop-icon").style.display = "";
      micBtn.title = "Stop recording";

      recordingSeconds = 0;
      recordingTimer = setInterval(function () {
        recordingSeconds++;
        if (recordingSeconds >= 120) stopRecording(); // 2 min max
      }, 1000);
    }).catch(function (err) {
      console.error("Microphone access denied", err);
      alert("Microphone access is required for audio recording.");
    });
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
    }
  }

  function discardAudio() {
    pendingAudioBlob = null;
    audioPreview.style.display = "none";
    audioPlayback.src = "";
  }

  micBtn.addEventListener("click", function () {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      stopRecording();
    } else {
      startRecording();
    }
  });

  discardAudioBtn.addEventListener("click", function () {
    discardAudio();
  });

  function blobToBase64(blob) {
    return new Promise(function (resolve) {
      var reader = new FileReader();
      reader.onloadend = function () {
        // Strip "data:audio/webm;base64," prefix
        resolve(reader.result.split(",")[1]);
      };
      reader.readAsDataURL(blob);
    });
  }

  // ── Submit handler ──
  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    var text = input.value.trim();
    var hasAudio = !!pendingAudioBlob;
    if (!text && !hasAudio) return;

    // Stop any in-progress recording
    if (mediaRecorder && mediaRecorder.state === "recording") {
      stopRecording();
      // Wait a moment for the stop event to fire
      await new Promise(function (r) { setTimeout(r, 200); });
      hasAudio = !!pendingAudioBlob;
    }

    // Auto-create session on first message if none active
    if (!currentSessionId) {
      try {
        var res = await fetch("/api/chat/sessions", { method: "POST" });
        var session = await res.json();
        currentSessionId = session.id;
        chatHistory = [];
      } catch (err) {
        addMessage("assistant", '<span class="error">Failed to create session</span>');
        return;
      }
    }

    // Build display message
    var displayHtml = "";
    if (hasAudio) {
      displayHtml += '<div class="user-audio-badge">Voice message</div>';
    }
    if (text) {
      displayHtml += renderMarkdown(text);
    }
    addMessage("user", displayHtml);

    // Build history entry (text only for session storage)
    var historyText = text || "(voice message)";
    chatHistory.push({ role: "user", parts: [{ text: historyText }] });

    // Prepare audio payload
    var audioBase64 = null;
    if (hasAudio) {
      audioBase64 = await blobToBase64(pendingAudioBlob);
      discardAudio();
    }

    input.value = "";
    setEnabled(false);

    // Auto-title from first user message
    var isFirst = chatHistory.filter(function (m) { return m.role === "user"; }).length === 1;

    try {
      var payload = { messages: chatHistory };
      if (audioBase64) {
        payload.audio = { data: audioBase64, mime_type: "audio/webm" };
      }
      var res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Server error: " + res.status);

      var data = await readStream(res);
      clearProgress();

      if (!data) throw new Error("No response received");
      if (data.error) throw new Error(data.error);

      var reply = data.text || "Sorry, I could not generate a response.";
      addMessage("assistant", renderMarkdown(reply));
      chatHistory.push({ role: "model", parts: [{ text: reply }] });

      if (data.tools_used && data.tools_used.length > 0) {
        var toolsLabel = document.createElement("div");
        toolsLabel.className = "tool-activity";
        toolsLabel.textContent = "Used: " + data.tools_used.join(", ");
        messagesEl.lastElementChild.appendChild(toolsLabel);
      }

      // Save session after each exchange
      var title = isFirst ? (text || "Voice message").substring(0, 50) : undefined;
      await saveSession(title);
    } catch (err) {
      clearProgress();
      addMessage("assistant", '<span class="error">Error: ' + err.message + "</span>");
    } finally {
      setEnabled(true);
      input.focus();
    }
  });

  // ── Init ──
  loadSessionList();
  input.focus();
})();
