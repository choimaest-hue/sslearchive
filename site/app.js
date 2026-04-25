(() => {
  const body = document.body;
  const toggle = document.getElementById("mobileWebToggle");

  const STORAGE_KEY = "ssletv-view-mode";
  const MIN_AD_WIDTH = 180;

  function initAds() {
    const adNodes = document.querySelectorAll('ins.adsbygoogle[data-ssletv-ad="true"]');
    if (!adNodes.length || body.classList.contains("mode-mobile")) {
      return;
    }

    for (const adNode of adNodes) {
      if (adNode.dataset.ssletvAdInit === "done") {
        continue;
      }

      const slotWidth = adNode.offsetWidth;
      if (slotWidth < MIN_AD_WIDTH) {
        continue;
      }

      (window.adsbygoogle = window.adsbygoogle || []).push({});
      adNode.dataset.ssletvAdInit = "done";
    }
  }

  function setMode(mode) {
    body.classList.remove("mode-mobile", "mode-web");
    body.classList.add(mode === "mobile" ? "mode-mobile" : "mode-web");
    if (toggle) {
      toggle.textContent = mode === "mobile" ? "웹으로 보기" : "모바일로 보기";
    }
    localStorage.setItem(STORAGE_KEY, mode);
    window.requestAnimationFrame(initAds);
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

  window.addEventListener("resize", () => {
    window.requestAnimationFrame(initAds);
  });

  initMode();
})();
