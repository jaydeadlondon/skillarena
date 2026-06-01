function enableFocusMode(enabled) {
  document.body.classList.toggle("focus-mode", enabled);
  localStorage.setItem("focusMode", enabled ? "1" : "0");
}
function detectActivityContext() {
  const path = window.location.pathname;
  let type = "general";
  let referenceId = null;
  if (path.startsWith("/learn/lessons/")) {
    type = "lesson";
    const match = path.match(/\/learn\/lessons\/(\d+)/);
    if (match) {
      referenceId = Number(match[1]);
    }
  } else if (path === "/dashboard") {
    type = "dashboard";
  } else if (path.startsWith("/courses")) {
    type = "course";
  } else if (path.startsWith("/pvp")) {
    type = "pvp";
  } else if (path.startsWith("/quests")) {
    type = "quests";
  } else if (path.startsWith("/shop")) {
    type = "shop";
  } else if (path.startsWith("/focus")) {
    type = "focus";
  } else if (path.startsWith("/profile")) {
    type = "profile";
  } else if (path.startsWith("/admin")) {
    type = "admin";
  }
  return { activity_type: type, reference_id: referenceId, path: path };
}
function startActivityTracker() {
  if (document.body.dataset.authenticated !== "true") {
    return;
  }
  let lastInteraction = Date.now();
  let activeSeconds = 0;
  const idleAfterMs = 60000;
  const heartbeatEverySeconds = 15;
  const markActive = () => {
    lastInteraction = Date.now();
  };
  ["mousemove", "keydown", "scroll", "click", "touchstart"].forEach(
    (eventName) =>
      document.addEventListener(eventName, markActive, { passive: true }),
  );
  const isActive = () =>
    document.visibilityState === "visible" &&
    Date.now() - lastInteraction < idleAfterMs;
  const sendHeartbeat = (seconds) => {
    if (seconds <= 0) {
      return;
    }
    const context = detectActivityContext();
    const payload = { ...context, seconds: seconds };
    const body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      if (navigator.sendBeacon("/activity/heartbeat", blob)) {
        return;
      }
    }
    fetch("/activity/heartbeat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => {});
  };
  setInterval(() => {
    if (isActive()) {
      activeSeconds += 5;
    }
    if (activeSeconds >= heartbeatEverySeconds) {
      sendHeartbeat(activeSeconds);
      activeSeconds = 0;
    }
  }, 5000);
  window.addEventListener("beforeunload", () => {
    if (activeSeconds > 0) {
      sendHeartbeat(activeSeconds);
    }
  });
}
document.addEventListener("DOMContentLoaded", () => {
  if (localStorage.getItem("focusMode") === "1") {
    document.body.classList.add("focus-mode");
  }
  document
    .querySelectorAll("[data-focus-toggle]")
    .forEach((btn) =>
      btn.addEventListener("click", () =>
        enableFocusMode(!document.body.classList.contains("focus-mode")),
      ),
    );
  document.addEventListener("keydown", (event) => {
    if (
      event.key === "Escape" &&
      document.body.classList.contains("focus-mode")
    ) {
      enableFocusMode(false);
    }
  });
  const pop = document.querySelector("[data-reward-pop]");
  if (pop) {
    setTimeout(() => pop.remove(), 3000);
  }
  startActivityTracker();
});
