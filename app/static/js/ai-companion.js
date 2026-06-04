(function () {
  const cfg = window.SkillArenaAI;
  if (!cfg) {
    return;
  }
  const status = document.getElementById("aiStatus");
  const responses = document.getElementById("aiResponses");
  const customForm = document.getElementById("aiCustomForm");
  const customPrompt = document.getElementById("aiCustomPrompt");
  let activeToast = null;
  let toastShownAt = 0;
  const MIN_THINKING_TOAST_MS = 900;

  function setStatus(text) {
    if (status) {
      status.textContent = text;
    }
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
    card.innerHTML = `<span class="badge">${promptType}</span><p></p>`;
    card.querySelector("p").textContent = text;
    responses.prepend(card);
  }
  async function askAI(action, prompt) {
    setStatus("");
    showToast("Thinking...", "thinking");
    const form = new FormData();
    form.append("action", action);
    form.append("custom_prompt", prompt || "");
    try {
      const response = await fetch(`/ai/lessons/${cfg.lessonId}/ask`, {
        method: "POST",
        body: form,
      });
      const data = await response.json();
      if (!data.ok) {
        showToast(data.error || "AI request failed.", "error");
        hideToast(2800);
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
    }
  }

  document.querySelectorAll("[data-ai-action]").forEach((button) => {
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
})();
