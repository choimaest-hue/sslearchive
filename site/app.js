(() => {
  const body = document.body;
  const toggle = document.getElementById("mobileWebToggle");

  const STORAGE_KEY = "ssletv-view-mode";

  function setMode(mode) {
    body.classList.remove("mode-mobile", "mode-web");
    body.classList.add(mode === "mobile" ? "mode-mobile" : "mode-web");
    if (toggle) {
      toggle.textContent = mode === "mobile" ? "웹으로 보기" : "모바일로 보기";
    }
    localStorage.setItem(STORAGE_KEY, mode);
  }

  function initMode() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "mobile" || saved === "web") {
      setMode(saved);
      return;
    }

    if (window.matchMedia("(max-width: 980px)").matches) {
      setMode("mobile");
      return;
    }

    setMode("web");
  }

  if (toggle) {
    toggle.addEventListener("click", () => {
      const next = body.classList.contains("mode-mobile") ? "web" : "mobile";
      setMode(next);
    });
  }

  initMode();
})();
