(function () {
  const cfg = window.SkillArenaAI;
  if (!cfg) {
    return;
  }
  const status = document.getElementById("aiStatus");
  const responses = document.getElementById("aiResponses");
  const customForm = document.getElementById("aiCustomForm");
  const customPrompt = document.getElementById("aiCustomPrompt");
  const clearHistoryButton = document.getElementById("aiClearHistoryButton");
  const actionButtons = Array.from(
    document.querySelectorAll("[data-ai-action]"),
  );
  const submitButton = customForm
    ? customForm.querySelector('button[type="submit"]')
    : null;
  let activeToast = null;
  let toastShownAt = 0;
  function csrfToken() {
    return document.body.dataset.csrfToken || "";
  }
  const MIN_THINKING_TOAST_MS = 900;

  function setStatus(text) {
    if (status) {
      status.textContent = text;
    }
  }
  function setLoading(isLoading) {
    actionButtons.forEach((button) => {
      button.disabled = isLoading;
    });
    if (submitButton) {
      submitButton.disabled = isLoading;
    }
    if (clearHistoryButton) {
      clearHistoryButton.disabled = isLoading;
    }
  }
  function escapeHtml(text) {
    return String(text)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
  function renderSimpleMarkdown(text) {
    let safe = escapeHtml(text || "");
    safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
    safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    const lines = safe.split(/\r?\n/);
    let html = "";
    let inList = false;
    for (const line of lines) {
      const trimmed = line.trim();
      if (/^[-*] /.test(trimmed)) {
        if (!inList) {
          html += "<ul>";
          inList = true;
        }
        html += `<li>${trimmed.replace(/^[-*] /, "")}</li>`;
      } else {
        if (inList) {
          html += "</ul>";
          inList = false;
        }
        if (trimmed) {
          html += `<p>${trimmed}</p>`;
        }
      }
    }
    if (inList) {
      html += "</ul>";
    }
    return html || "<p></p>";
  }
  function showToast(text, variant) {
    if (activeToast) {
      activeToast.remove();
    }
    const toast = document.createElement("div");
    toast.className = `ai-toast ${variant || ""}`.trim();
    toast.textContent = text;
    document.body.appendChild(toast);
    activeToast = toast;
    toastShownAt = Date.now();
    return toast;
  }
  function hideToast(delay) {
    const toast = activeToast;
    if (!toast) {
      return;
    }
    const elapsed = Date.now() - toastShownAt;
    const wait = Math.max(delay || 0, MIN_THINKING_TOAST_MS - elapsed);
    setTimeout(() => {
      toast.classList.add("hide");
      setTimeout(() => toast.remove(), 220);
      if (activeToast === toast) {
        activeToast = null;
      }
    }, wait);
  }
  function addResponse(promptType, text) {
    if (!responses) {
      return;
    }
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<span class="badge">${escapeHtml(promptType)}</span><div class="ai-rendered-response"></div>`;
    card.querySelector(".ai-rendered-response").innerHTML =
      renderSimpleMarkdown(text);
    responses.prepend(card);
  }
  async function askAI(action, prompt) {
    setStatus("");
    setLoading(true);
    showToast("Thinking...", "thinking");
    const form = new FormData();
    form.append("action", action);
    form.append("custom_prompt", prompt || "");
    form.append("csrf_token", csrfToken());
    try {
      const response = await fetch(`/ai/lessons/${cfg.lessonId}/ask`, {
        method: "POST",
        body: form,
      });
      const data = await response.json();
      if (!data.ok) {
        const limitReached = (data.error || "").toLowerCase().includes("limit");
        showToast(
          limitReached
            ? "Daily AI limit reached."
            : data.error || "AI request failed.",
          "error",
        );
        hideToast(3000);
        if (data.fallback) {
          addResponse("fallback", data.fallback);
        }
        return;
      }
      hideToast(250);
      addResponse(data.prompt_type, data.response);
    } catch (e) {
      showToast("AI assistant is unavailable right now.", "error");
      hideToast(2800);
      addResponse(
        "fallback",
        "Try one tiny step: write a one-sentence summary of what you just watched.",
      );
    } finally {
      setLoading(false);
    }
  }

  actionButtons.forEach((button) => {
    button.addEventListener("click", () => askAI(button.dataset.aiAction, ""));
  });
  if (customForm) {
    customForm.addEventListener("submit", (event) => {
      event.preventDefault();
      askAI("custom", customPrompt ? customPrompt.value : "");
      if (customPrompt) {
        customPrompt.value = "";
      }
    });
  }
  if (clearHistoryButton) {
    clearHistoryButton.addEventListener("click", async () => {
      const confirmed = window.confirm(
        "Are you sure you want to clear this dialogue history? This action cannot be undone.",
      );
      if (!confirmed) {
        return;
      }
      setLoading(true);
      try {
        const response = await fetch(`/ai/lessons/${cfg.lessonId}/history`, {
          method: "DELETE",
          headers: { "X-CSRF-Token": csrfToken() },
        });
        const data = await response.json();
        if (data.ok && responses) {
          responses.innerHTML = "";
          showToast("AI dialogue history cleared.", "thinking");
          hideToast(1600);
        } else {
          showToast("Could not clear AI history.", "error");
          hideToast(2600);
        }
      } catch (e) {
        showToast("Could not clear AI history.", "error");
        hideToast(2600);
      } finally {
        setLoading(false);
      }
    });
  }
  document.querySelectorAll(".ai-rendered-response").forEach((node) => {
    node.innerHTML = renderSimpleMarkdown(node.textContent || "");
  });
})();
