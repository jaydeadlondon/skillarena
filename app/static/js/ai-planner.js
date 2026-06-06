(function () {
  const button = document.getElementById("aiPlannerButton");
  const status = document.getElementById("aiPlannerStatus");
  const result = document.getElementById("aiPlannerResult");
  if (!button || !result) {
    return;
  }

  function setStatus(text) {
    if (status) {
      status.textContent = text;
    }
  }
  function showResult(text) {
    result.style.display = "block";
    result.textContent = text;
  }

  button.addEventListener("click", async () => {
    button.disabled = true;
    setStatus("Thinking...");
    try {
      const response = await fetch("/ai/dashboard/plan", {
        method: "POST",
        headers: { "X-CSRF-Token": document.body.dataset.csrfToken || "" },
      });
      const data = await response.json();
      if (!data.ok) {
        setStatus(data.error || "AI planner failed.");
        if (data.fallback) {
          showResult(data.fallback);
        }
        return;
      }
      setStatus("");
      showResult(data.response);
    } catch (e) {
      setStatus("AI planner is unavailable right now.");
      showResult(
        "Action: Continue your next lesson\nWhy: It is the simplest way to make visible progress today.",
      );
    } finally {
      button.disabled = false;
    }
  });
})();
