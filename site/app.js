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

// ─── Random Post ─────────────────────────────────────
(() => {
  const container = document.querySelector('.random-btns');
  if (!container) return;
  const indexUrl = container.dataset.index || 'search-index.json';
  const rootPrefix = indexUrl.replace('search-index.json', '');
  const ssulBtn = document.getElementById('randomSsulBtn');
  const lanovelBtn = document.getElementById('randomLanovelBtn');

  let cache = null;

  async function getIndex() {
    if (cache) return cache;
    try {
      const res = await fetch(indexUrl);
      cache = await res.json();
    } catch (_) { cache = []; }
    return cache;
  }

  function pickRandom(items) {
    return items[Math.floor(Math.random() * items.length)];
  }

  if (ssulBtn) {
    ssulBtn.addEventListener('click', async e => {
      e.preventDefault();
      const index = await getIndex();
      const ssul = index.filter(x => x.T === 's');
      if (!ssul.length) return;
      const item = pickRandom(ssul);
      window.location.href = rootPrefix + 'posts/' + item.i + '.html';
    });
    ssulBtn.addEventListener('mouseenter', () => getIndex(), { once: true });
  }

  if (lanovelBtn) {
    lanovelBtn.addEventListener('click', async e => {
      e.preventDefault();
      const index = await getIndex();
      const lanovel = index.filter(x => x.T === 'l');
      if (!lanovel.length) return;
      const item = pickRandom(lanovel);
      window.location.href = rootPrefix + 'lanovel-posts/' + item.i + '.html';
    });
    lanovelBtn.addEventListener('mouseenter', () => getIndex(), { once: true });
  }
})();

// ─── Search ──────────────────────────────────────────
(() => {
  const overlay = document.getElementById('searchOverlay');
  if (!overlay) return;

  const bg = document.getElementById('searchOverlayBg');
  const closeBtn = document.getElementById('searchClose');
  const toggle = document.getElementById('searchToggle');
  const input = document.getElementById('searchInput');
  const results = document.getElementById('searchResults');
  const indexUrl = overlay.dataset.index || 'search-index.json';
  const rootPrefix = indexUrl.replace('search-index.json', '');

  let cache = null;
  let timer = null;

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  async function loadIndex() {
    if (cache !== null) return cache;
    try {
      const res = await fetch(indexUrl);
      cache = await res.json();
    } catch (_) {
      cache = [];
    }
    return cache;
  }

  function filterIndex(q, index) {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    return index.filter(item => {
      const hay = (item.t + ' ' + (item.c || '') + ' ' + (item.e || '')).toLowerCase();
      return words.every(w => hay.includes(w));
    }).slice(0, 40);
  }

  function renderResults(hits, q) {
    if (!hits.length) {
      results.innerHTML = '<p class="search-no-results">"' + escHtml(q) + '"에 대한 결과가 없습니다</p>';
      return;
    }
    results.innerHTML = hits.map(item => {
      const href = item.T === 'l'
        ? rootPrefix + 'lanovel-posts/' + item.i + '.html'
        : rootPrefix + 'posts/' + item.i + '.html';
      const tag = item.T === 'l' ? '라노벨' : (item.c || '썰');
      return '<a href="' + href + '" class="search-result-item">'
        + '<div class="search-result-meta">'
        + '<span class="search-result-tag">' + escHtml(tag) + '</span>'
        + '<span class="search-result-date">' + escHtml(item.d || '') + '</span>'
        + '</div>'
        + '<div class="search-result-title">' + escHtml(item.t) + '</div>'
        + (item.e ? '<div class="search-result-excerpt">' + escHtml(item.e) + '</div>' : '')
        + '</a>';
    }).join('');
  }

  function openOverlay() {
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    if (input) { input.focus(); input.select(); }
    loadIndex();
  }

  function closeOverlay() {
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  if (toggle) toggle.addEventListener('click', openOverlay);
  if (closeBtn) closeBtn.addEventListener('click', closeOverlay);
  if (bg) bg.addEventListener('click', closeOverlay);

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeOverlay();
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openOverlay(); }
  });

  if (input) {
    input.addEventListener('input', () => {
      const q = input.value;
      clearTimeout(timer);
      if (!q.trim()) {
        results.innerHTML = '<p class="search-hint">검색어를 입력하세요</p>';
        return;
      }
      timer = setTimeout(async () => {
        const index = await loadIndex();
        renderResults(filterIndex(q, index), q);
      }, 180);
    });
  }
})();
