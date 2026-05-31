function enableFocusMode(enabled) {
  document.body.classList.toggle("focus-mode", enabled);
  localStorage.setItem("focusMode", enabled ? "1" : "0");
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
});
