function detectActivityContext() {
  const path = window.location.pathname;
  let type = "general";
  let referenceId = null;
  if (path.startsWith("/learn/lessons/")) {
    type = "course";
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
  } else if (path.startsWith("/notifications")) {
    type = "general";
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
function spawnRewardConfetti() {
  const colors = ["#f7c948", "#8b5cf6", "#36d399", "#fb923c", "#f5f0df"];
  for (let i = 0; i < 26; i++) {
    const piece = document.createElement("span");
    piece.className = "confetti-piece";
    piece.style.left = `${Math.random() * 100}vw`;
    piece.style.background = colors[Math.floor(Math.random() * colors.length)];
    piece.style.animationDelay = `${Math.random() * 0.35}s`;
    piece.style.transform = `rotate(${Math.random() * 360}deg)`;
    document.body.appendChild(piece);
    setTimeout(() => piece.remove(), 2200);
  }
}
document.addEventListener("DOMContentLoaded", () => {
  localStorage.removeItem("focusMode");
  const pop = document.querySelector("[data-reward-pop]");
  if (pop) {
    pop.classList.add("reward-pop");
    spawnRewardConfetti();
    setTimeout(() => pop.remove(), 3600);
  }
  startActivityTracker();
});
