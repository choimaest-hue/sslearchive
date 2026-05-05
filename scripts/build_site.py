import argparse
import html
import json
import re
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

CATEGORIES = [
  "군대 썰",
  "육아 썰",
  "연애/결혼 썰",
  "직장/사회 썰",
  "학교/학원 썰",
  "가족/친척 썰",
  "공포/사건 썰",
  "기타 화제 썰",
]
SLUG = {
  "군대 썰": "military",
  "육아 썰": "parenting",
  "연애/결혼 썰": "love-marriage",
  "직장/사회 썰": "work-society",
  "학교/학원 썰": "school-academy",
  "가족/친척 썰": "family-relatives",
  "공포/사건 썰": "horror-incident",
  "기타 화제 썰": "hot-issue",
}
DEFAULT_PER_PAGE = 10
INDEX_SITE_URL = "https://sslearchive.vercel.app"
ORIGINAL_HOME_URL = "https://ssletv.com"
ADSENSE_CLIENT = ""
ADSENSE_HOST = ""
CONTACT_EMAIL = "choimaest@naver.com"
SUPPORT_EMAIL_SUBJECT = "[썰TV] 문의/후원 요청"
SUPPORT_PLATFORMS: list[tuple[str, str]] = [
    ("Toss", "https://toss.me/choimaest"),
]
NAVER_SITE_VERIFICATION = "36275f7ef596c60eff1322aa781657cefd4a75f9"
GOOGLE_SITE_VERIFICATION = "p1sOyazCjOMOi4Nt9AcF9jaIzoxvRR0FT0sgwoTxMRY"
BING_SITE_VERIFICATION = ""
MIN_INDEXABLE_TEXT_CHARS = 300
FAVICON_HREF = "/favicon.ico"
THEME_COLOR = "#b83b2f"
ASSET_VERSION = "20260505-support-refresh"
FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="SSUL TV">
    <rect x="2" y="2" width="60" height="60" rx="14" fill="#b83b2f"/>
    <path d="M15 19.5c0-4.1 3.3-7.5 7.5-7.5h19c4.1 0 7.5 3.4 7.5 7.5v18c0 4.1-3.4 7.5-7.5 7.5H31.4L21 53v-8h1.5c-4.2 0-7.5-3.4-7.5-7.5v-18Z" fill="#fff8ef"/>
    <circle cx="45" cy="23" r="3.6" fill="#0f766e"/>
    <path d="M22 47h20" stroke="#55231f" stroke-width="4" stroke-linecap="round"/>
    <text x="32" y="35" text-anchor="middle" font-size="14" font-family="Arial, sans-serif" font-weight="800" fill="#231f20">SSUL</text>
    <path d="M23 38h18" stroke="#d99a2b" stroke-width="2.5" stroke-linecap="round"/>
</svg>
"""

# Optional ad network hooks. Leave empty until each network issues real IDs.
# Placements are intentionally conservative: one sidebar stack on desktop and
# one in-content unit per major flow, so ads do not interrupt reading.
AD_PLACEMENTS: dict[str, dict[str, Any]] = {
    "home-between": {"label": "광고", "min_height": 120, "guide": "desktop 728x90, mobile 320x100"},
    "list-bottom": {"label": "광고", "min_height": 180, "guide": "desktop 728x90, mobile 320x100"},
    "sidebar-top": {"label": "광고", "min_height": 280, "guide": "desktop 300x250"},
    "sidebar-bottom": {"label": "광고", "min_height": 220, "guide": "desktop 300x250"},
    "article-bottom": {"label": "광고", "min_height": 200, "guide": "desktop 728x90 or 336x280, mobile 320x100"},
}

KakaoAdFitUnit = tuple[str, int, int]
KakaoAdFitConfig = KakaoAdFitUnit | dict[str, KakaoAdFitUnit]

# Fill after Kakao AdFit issues ad unit IDs. Each placement accepts either one
# unit tuple or responsive variants, for example:
# KAKAO_ADFIT_UNITS = {
#     "article-bottom": {
#         "mobile": ("DAN-mobile-id", 320, 100),
#         "desktop": ("DAN-desktop-id", 728, 90),
#     }
# }
KAKAO_ADFIT_UNITS: dict[str, KakaoAdFitConfig] = {}

# Fill after AdSense display ad units are created. The value is data-ad-slot.
# ADSENSE_UNITS = {"article-bottom": "1234567890"}
ADSENSE_UNITS: dict[str, str] = {}
DABLE_SERVICE_NAME = ""
DABLE_WIDGETS: dict[str, str] = {}

CATEGORY_DESCRIPTIONS = {
    "군대 썰": "군 생활, 훈련소, 예비군처럼 경험담 중심으로 읽을 수 있는 군대 썰 모음입니다.",
    "육아 썰": "육아와 가족 일상에서 나온 고민, 경험담, 공감형 이야기를 모았습니다.",
    "연애/결혼 썰": "연애, 결혼 준비, 부부와 가족 관계에서 나온 실제 고민형 이야기를 정리했습니다.",
    "직장/사회 썰": "회사 생활, 인간관계, 사회생활에서 나온 사건과 경험담을 볼 수 있습니다.",
    "학교/학원 썰": "학교와 학원 생활에서 생긴 이야기와 고민을 모은 카테고리입니다.",
    "가족/친척 썰": "가족, 친척, 명절과 집안일을 둘러싼 이야기를 정리했습니다.",
    "공포/사건 썰": "공포, 사건, 이상한 경험담처럼 긴장감 있는 썰을 모았습니다.",
    "기타 화제 썰": "특정 카테고리로 묶기 어려운 화제성 이야기를 모았습니다.",
}


def esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def is_external_url(url: str) -> bool:
    return url.startswith(("http://", "https://", "data:"))


def media_src(url: str, prefix: str = "") -> str:
    value = str(url or "").strip()
    if not value or is_external_url(value):
        return value
    value = value.lstrip("/")
    if value.startswith("../"):
        return value
    clean_prefix = prefix.strip("/")
    return f"{clean_prefix}/{value}" if clean_prefix else value


def media_abs(url: str, site_url: str) -> str:
    value = str(url or "").strip()
    if not value or is_external_url(value):
        return value
    return f"{site_url.rstrip('/')}/{value.lstrip('/')}"


def ensure(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    if size <= 0:
        size = DEFAULT_PER_PAGE
    return [items[i : i + size] for i in range(0, len(items), size)] or [[]]


def list_page_name(base: str, page: int) -> str:
    return f"{base}.html" if page <= 1 else f"{base}-page-{page}.html"


def pagination_html(base: str, current: int, total: int) -> str:
    if total <= 1:
        return ""

    numbers = []
    start = max(1, current - 2)
    end = min(total, current + 2)

    if start > 1:
        numbers.append(f'<a class="page-link" href="{list_page_name(base, 1)}">1</a>')
        if start > 2:
            numbers.append('<span class="page-ellipsis">···</span>')

    for page in range(start, end + 1):
        cls = "page-link current" if page == current else "page-link"
        numbers.append(f'<a class="{cls}" href="{list_page_name(base, page)}">{page}</a>')

    if end < total:
        if end < total - 1:
            numbers.append('<span class="page-ellipsis">···</span>')
        numbers.append(f'<a class="page-link" href="{list_page_name(base, total)}">{total}</a>')

    return (
        '<nav class="pagination" aria-label="페이지 이동">'
        f"{''.join(numbers)}"
        "</nav>"
    )


def header_html(active: str, prefix: str = "") -> str:
    ssul_cls = "main-nav-link active" if active == "ssul" else "main-nav-link"
    lanovel_cls = "main-nav-link active" if active == "lanovel" else "main-nav-link"
    p = prefix + "/" if prefix else ""
    home_href = "../" if prefix else "./"
    idx_path = f"{prefix}/search-index.json" if prefix else "search-index.json"
    return f"""
<header class="site-header">
  <div class="site-header-inner">
                <a href="{home_href}" class="brand" aria-label="썰TV 홈">
                    <img src="/assets/brand/logo-mark.svg" class="brand-logo" width="30" height="30" alt="" aria-hidden="true" />
                    <span>썰TV</span>
                </a>
    <div class="header-actions">
      <nav class="main-nav" aria-label="메인 주제">
        <a href="{p}ssul.html" class="{ssul_cls}">썰 아카이브</a>
        <a href="{p}lanovel.html" class="{lanovel_cls}">라노벨 아카이브</a>
      </nav>
      <button class="search-btn" id="searchToggle" aria-label="검색 열기" type="button">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      </button>
    </div>
  </div>
</header>
<div class="search-overlay" id="searchOverlay" aria-hidden="true" data-index="{idx_path}">
  <div class="search-overlay-bg" id="searchOverlayBg"></div>
  <div class="search-overlay-panel">
    <div class="search-field-row">
      <svg class="search-field-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="search" id="searchInput" class="search-input" placeholder="제목, 카테고리 검색..." autocomplete="off" spellcheck="false" />
      <button class="search-close-btn" id="searchClose" aria-label="검색 닫기" type="button">✕</button>
    </div>
    <div class="search-results" id="searchResults">
      <p class="search-hint">검색어를 입력하세요</p>
    </div>
  </div>
</div>
"""


def footer_html(prefix: str = "") -> str:
    p = prefix + "/" if prefix else ""
    return f"""
<footer class="site-footer">
  <div class="site-footer-inner">
    <span class="footer-brand">썰TV</span>
    <span>·</span>
    <a href="{p}ssul.html">썰 아카이브</a>
    <span>·</span>
    <a href="{p}lanovel.html">라노벨 아카이브</a>
    <span>·</span>
    <a href="{p}contact.html">문의/후원</a>
    <span>·</span>
    <span>© 2025 썰TV</span>
  </div>
</footer>
"""


def mailto_url(address: str, subject: str = "", body: str = "") -> str:
    query: list[str] = []
    if subject:
        query.append(f"subject={quote(subject)}")
    if body:
        query.append(f"body={quote(body)}")
    query_text = "&".join(query)
    return f"mailto:{address}?{query_text}" if query_text else f"mailto:{address}"


def plain_excerpt(text: str, fallback: str = "", limit: int = 140) -> str:
    raw = re.sub(r"https?://\S+", "", text or "")
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        raw = (fallback or "").strip()
    if not raw:
        return "요약 정보가 없습니다."
    if len(raw) > limit:
        return raw[:limit].rstrip() + "..."
    return raw


def atom_date(value: str) -> str:
    try:
        parsed = datetime.fromisoformat((value or "").strip())
    except ValueError:
        parsed = datetime.now(UTC)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def content_text_len(*values: Any) -> int:
    text = " ".join(str(value or "") for value in values)
    return len(re.sub(r"\s+", "", text))


def is_indexable_ssul(item: dict[str, Any]) -> bool:
    return content_text_len(item.get("body"), item.get("summary")) >= MIN_INDEXABLE_TEXT_CHARS


def is_indexable_lanovel(item: dict[str, Any]) -> bool:
    return content_text_len(
        item.get("content"),
        item.get("summary"),
        item.get("excerpt"),
        item.get("synopsis"),
    ) >= MIN_INDEXABLE_TEXT_CHARS


def parse_date_safe(value: str) -> datetime:
    try:
        return datetime.fromisoformat((value or "").strip())
    except ValueError:
        return datetime(1970, 1, 1)


def ssul_card_html(item: dict[str, Any]) -> str:
    title = esc(item.get("title", ""))
    summary = esc(plain_excerpt(item.get("summary") or item.get("body") or "", item.get("title", ""), 120))
    cat = esc(item.get("category", "기타"))
    pid = esc(item.get("id", ""))
    date = esc(item.get("published_at", ""))
    comments = int(item.get("comment_count") or 0)
    source = esc(item.get("source_url", ""))
    return (
        f'<article class="card" data-category="{cat}">'
        f'<span class="card-tag">{cat}</span>'
        f'<h3><a href="posts/{pid}.html">{title}</a></h3>'
        f"<p>{summary}</p>"
        f'<div class="meta"><span>{date}</span><span>댓글 {comments}</span></div>'
        f'<p class="source-line"><a href="{source}" rel="nofollow noopener" target="_blank">원문 보기</a></p>'
        "</article>"
    )


def lanovel_card_html(item: dict[str, Any]) -> str:
    title = esc(item.get("title", ""))
    pid = esc(item.get("id", ""))
    date = esc(item.get("published_at", ""))
    summary = esc(lanovel_list_summary(item))
    _raw_thumb = (item.get("image_urls") or [""])[0]
    thumb = esc(media_src(_raw_thumb or "assets/lanovel/default-cover.webp"))  # fallback to default cover
    ncode_url = esc(item.get("ncode_url", ""))

    thumb_html = f'<img class="lanovel-thumb" src="{thumb}" alt="{title}" loading="lazy" />'
    ncode_html = (
        f'<p class="source-line"><a href="{ncode_url}" rel="nofollow noopener" target="_blank">원작 바로가기</a></p>'
        if ncode_url
        else ""
    )
    return (
        '<article class="card card-compact">'
        '<span class="card-tag">라노벨</span>'
        f"{thumb_html}"
        f'<h3><a href="lanovel-posts/{pid}.html">{title}</a></h3>'
        f'<p class="preview-summary">{summary}</p>'
        f"{ncode_html}"
        f'<div class="meta"><span>라노벨</span><span>{date}</span></div>'
        "</article>"
    )


def linkify_text(text: str) -> str:
    pattern = re.compile(r"(https?://[^\s<]+)")

    def _replace(match: re.Match[str]) -> str:
        url = match.group(1)
        safe_url = esc(url)
        return f'<a href="{safe_url}" rel="nofollow noopener" target="_blank">{safe_url}</a>'

    return pattern.sub(_replace, esc(text))


def lanovel_content_html(item: dict[str, Any]) -> str:
    content = item.get("content", "") or ""
    lines = [line.strip() for line in content.split("\n")]
    paragraphs = [line for line in lines if line]

    if not paragraphs:
        return "<p>본문 데이터 없음</p>"

    rendered = []
    for line in paragraphs:
        rendered.append(f'<p class="content-paragraph">{linkify_text(line)}</p>')
    return "".join(rendered)


def lanovel_list_summary(item: dict[str, Any]) -> str:
    raw = (item.get("summary") or item.get("excerpt") or item.get("content") or "").strip()
    raw = re.sub(r"https?://\S+", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if not raw:
        return "요약 정보가 없습니다."
    if len(raw) > 120:
        return raw[:120].rstrip() + "..."
    return raw


def related_posts_nav(items: list[dict[str, Any]], current_id: str, limit: int = 5) -> str:
    try:
        current_idx = next(i for i, item in enumerate(items) if item.get("id") == current_id)
    except StopIteration:
        return ""

    prev_items = items[max(0, current_idx - limit):current_idx]
    next_items = items[current_idx + 1:min(len(items), current_idx + 1 + limit)]

    prev_post = prev_items[-1] if prev_items else None
    next_post = next_items[0] if next_items else None

    nav_html = ""
    if prev_post or next_post:
        nav_html += '<nav class="post-nav">'
        if prev_post:
            prev_title = esc(prev_post.get("title", ""))
            prev_id = esc(prev_post.get("id", ""))
            nav_html += (
                f'<a href="{prev_id}.html" class="post-nav-item">'
                f'<span class="post-nav-label">← 이전글</span>'
                f'<span class="post-nav-title">{prev_title}</span>'
                f'</a>'
            )
        else:
            nav_html += '<div></div>'
        if next_post:
            next_title = esc(next_post.get("title", ""))
            next_id = esc(next_post.get("id", ""))
            nav_html += (
                f'<a href="{next_id}.html" class="post-nav-item next">'
                f'<span class="post-nav-label">다음글 →</span>'
                f'<span class="post-nav-title">{next_title}</span>'
                f'</a>'
            )
        nav_html += '</nav>'

    related_items = []
    if prev_items and len(prev_items) > 1:
        related_items.extend(reversed(prev_items[:-1][:3]))
    if next_items and len(next_items) > 1:
        related_items.extend(next_items[1:3])

    if related_items:
        nav_html += '<section class="related-posts"><h3>관련 글 더보기</h3><div class="related-grid">'
        for item in related_items:
            title = esc(item.get("title", ""))
            pid = esc(item.get("id", ""))
            cat = esc(item.get("category", "기타"))
            nav_html += (
                f'<a href="{pid}.html" class="related-post">'
                f'<span class="related-cat">{cat}</span>'
                f'<span class="related-title">{title}</span>'
                f'</a>'
            )
        nav_html += '</div></section>'

    return nav_html


def site_json_ld(site_url: str, *entities: dict[str, Any]) -> str:
    organization_id = f"{site_url}/#organization"
    website_id = f"{site_url}/#website"
    graph: list[dict[str, Any]] = [
        {
            "@type": "Organization",
            "@id": organization_id,
            "name": "썰TV",
            "url": site_url,
            "logo": f"{site_url}/assets/brand/logo-512.png",
        },
        {
            "@type": "WebSite",
            "@id": website_id,
            "name": "썰TV",
            "url": site_url,
            "inLanguage": "ko-KR",
            "publisher": {"@id": organization_id},
        },
    ]
    graph.extend(entity for entity in entities if entity)
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))


def shared_head_meta(site_url: str) -> str:
    return f"""
    <meta name="theme-color" content="{THEME_COLOR}" />
    <meta name="application-name" content="썰TV" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-title" content="썰TV" />
    <meta name="apple-mobile-web-app-status-bar-style" content="default" />
    <meta name="mobile-web-app-capable" content="yes" />
    <meta name="msapplication-TileColor" content="{THEME_COLOR}" />
    <link rel="manifest" href="/site.webmanifest" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="icon" sizes="32x32" href="/favicon.ico" />
    <link rel="apple-touch-icon" href="/assets/brand/icon-192.png" />
    <link rel="sitemap" type="application/xml" title="Sitemap" href="{site_url}/sitemap.xml" />
    <link rel="alternate" type="application/atom+xml" title="썰TV 최신 글" href="{site_url}/feed.xml" />
""".strip()


def verification_meta_html() -> str:
    metas: list[str] = []
    if NAVER_SITE_VERIFICATION:
        metas.append(f'<meta name="naver-site-verification" content="{esc(NAVER_SITE_VERIFICATION)}" />')
    if GOOGLE_SITE_VERIFICATION:
        metas.append(f'<meta name="google-site-verification" content="{esc(GOOGLE_SITE_VERIFICATION)}" />')
    if BING_SITE_VERIFICATION:
        metas.append(f'<meta name="msvalidate.01" content="{esc(BING_SITE_VERIFICATION)}" />')
    return "\n    ".join(metas)


def site_manifest_json() -> str:
    payload = {
        "name": "썰TV",
        "short_name": "썰TV",
        "description": "썰과 라노벨을 주제별로 정리한 아카이브",
        "id": "/",
        "lang": "ko-KR",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui", "browser"],
        "orientation": "portrait-primary",
        "background_color": "#f7f4ef",
        "theme_color": THEME_COLOR,
        "categories": ["entertainment", "books", "news"],
        "prefer_related_applications": False,
        "related_applications": [],
        "icons": [
            {
                "src": "/assets/brand/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/assets/brand/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/assets/brand/icon-maskable-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
        "screenshots": [
            {
                "src": "/assets/brand/screenshot-wide.png",
                "sizes": "1366x768",
                "type": "image/png",
                "form_factor": "wide",
                "label": "썰TV 라노벨 아카이브 데스크톱 화면",
            },
            {
                "src": "/assets/brand/screenshot-mobile.png",
                "sizes": "390x844",
                "type": "image/png",
                "form_factor": "narrow",
                "label": "썰TV 모바일 아카이브 화면",
            },
        ],
        "shortcuts": [
            {
                "name": "썰 아카이브",
                "short_name": "썰",
                "url": "/ssul.html",
                "icons": [{"src": "/assets/brand/icon-192.png", "sizes": "192x192", "type": "image/png"}],
            },
            {
                "name": "라노벨 아카이브",
                "short_name": "라노벨",
                "url": "/lanovel.html",
                "icons": [{"src": "/assets/brand/icon-192.png", "sizes": "192x192", "type": "image/png"}],
            },
        ],
        "serviceworker": {
            "src": "/sw.js",
            "scope": "/",
            "use_cache": False,
        },
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def service_worker_js() -> str:
        return """const SSLETV_CACHE_VERSION = "__ASSET_VERSION__";
const CORE_CACHE = `ssletv-core-${SSLETV_CACHE_VERSION}`;
const RUNTIME_CACHE = `ssletv-runtime-${SSLETV_CACHE_VERSION}`;
const MAX_RUNTIME_ENTRIES = 90;

const CORE_ASSETS = [
    "/",
    "/index.html",
    "/ssul.html",
    "/lanovel.html",
    "/styles.css?v=__ASSET_VERSION__",
    "/app.js?v=__ASSET_VERSION__",
    "/site.webmanifest",
    "/favicon.svg",
    "/favicon.ico",
    "/assets/brand/logo-mark.svg",
    "/assets/brand/icon-192.png",
    "/assets/brand/icon-512.png",
    "/assets/brand/icon-maskable-512.png"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CORE_CACHE)
            .then(cache => cache.addAll(CORE_ASSETS.map(url => new Request(url, { cache: "reload" }))))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(keys
                .filter(key => key.startsWith("ssletv-") && key !== CORE_CACHE && key !== RUNTIME_CACHE)
                .map(key => caches.delete(key))))
            .then(() => self.clients.claim())
    );
});

async function trimRuntimeCache() {
    const cache = await caches.open(RUNTIME_CACHE);
    const keys = await cache.keys();
    if (keys.length <= MAX_RUNTIME_ENTRIES) return;
    await cache.delete(keys[0]);
    return trimRuntimeCache();
}

async function networkFirst(request) {
    const cache = await caches.open(RUNTIME_CACHE);
    try {
        const response = await fetch(request);
        if (response && response.ok) {
            cache.put(request, response.clone());
            trimRuntimeCache();
        }
        return response;
    } catch (_) {
        const cached = await caches.match(request);
        return cached || caches.match("/index.html");
    }
}

async function staleWhileRevalidate(request) {
    const cache = await caches.open(RUNTIME_CACHE);
    const cached = await cache.match(request);
    const fetched = fetch(request).then(response => {
        if (response && response.ok) {
            cache.put(request, response.clone());
            trimRuntimeCache();
        }
        return response;
    }).catch(() => cached);
    return cached || fetched;
}

self.addEventListener("fetch", event => {
    const request = event.request;
    if (request.method !== "GET") return;

    const url = new URL(request.url);
    if (url.origin !== self.location.origin) return;

    const acceptsHtml = request.headers.get("accept")?.includes("text/html");
    if (request.mode === "navigate" || acceptsHtml) {
        event.respondWith(networkFirst(request));
        return;
    }

    if (["style", "script", "worker", "manifest", "image", "font"].includes(request.destination)) {
        event.respondWith(staleWhileRevalidate(request));
    }
});
""".replace("__ASSET_VERSION__", ASSET_VERSION)


def breadcrumb_json_ld(site_url: str, crumbs: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": idx,
                "name": name,
                "item": f"{site_url}{path}",
            }
            for idx, (name, path) in enumerate(crumbs, start=1)
        ],
    }


def build_json_ld(items: list[dict[str, Any]], site_url: str, path_prefix: str) -> str:
    elements = []
    for idx, item in enumerate(items[:20], start=1):
        elements.append(
            {
                "@type": "ListItem",
                "position": idx,
                "url": f"{site_url}/{path_prefix}/{item.get('id', '')}.html",
                "name": item.get("title", ""),
            }
        )
    payload = {
        "@type": "ItemList",
        "itemListElement": elements,
    }
    return site_json_ld(site_url, payload)


def ad_scripts_html(include_ads: bool = True) -> str:
    if not include_ads:
        return ""

    scripts: list[str] = []
    if ADSENSE_CLIENT:
        scripts.append(
            f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>'
        )
    if KAKAO_ADFIT_UNITS:
        scripts.append('<script async src="https://t1.daumcdn.net/kas/static/ba.min.js"></script>')
    if DABLE_SERVICE_NAME and DABLE_WIDGETS:
        service = esc(DABLE_SERVICE_NAME)
        scripts.append(
            "<script>"
            "(function(d,a,b,l,e,_){d[b]=d[b]||function(){(d[b].q=d[b].q||[]).push(arguments)};"
            "e=a.createElement(l);e.async=1;e.charset='utf-8';e.src='https://static.dable.io/dist/plugin.min.js';"
            "_=a.getElementsByTagName(l)[0];_.parentNode.insertBefore(e,_);})(window,document,'dable','script');"
            f"dable('setService','{service}');dable('sendLogOnce');"
            "</script>"
        )
    return "\n  ".join(scripts)


def kakao_adfit_units_for(placement: str) -> list[tuple[str, str, int, int]]:
    config = KAKAO_ADFIT_UNITS.get(placement)
    if not config:
        return []
    if isinstance(config, tuple):
        unit_id, width, height = config
        return [("all", unit_id, width, height)]

    units: list[tuple[str, str, int, int]] = []
    seen: set[str] = set()
    for variant in ("mobile", "desktop", "all"):
        unit = config.get(variant)
        if unit:
            unit_id, width, height = unit
            units.append((variant, unit_id, width, height))
            seen.add(variant)
    for variant, unit in config.items():
        if variant in seen:
            continue
        unit_id, width, height = unit
        units.append((variant, unit_id, width, height))
    return units


def ad_variant_class(variant: str) -> str:
    if variant == "mobile":
        return " ad-variant-mobile"
    if variant == "desktop":
        return " ad-variant-desktop"
    return ""


def ad_unit_html(label: str | None = None, min_height: int | None = None, placement: str = "sidebar") -> str:
    policy = AD_PLACEMENTS.get(placement, {})
    label = label or str(policy.get("label", "광고"))
    min_height = int(min_height or policy.get("min_height", 250))
    kakao_units = kakao_adfit_units_for(placement)
    if kakao_units:
        blocks = []
        for variant, unit_id, width, height in kakao_units:
            variant_class = ad_variant_class(variant)
            variant_suffix = f":{variant}" if variant != "all" else ""
            blocks.append(f"""
<div class="ad-unit ad-slot{variant_class}" data-ad-unit data-ad-state="pending" data-ad-provider="kakao" data-ad-placement="{esc(placement + variant_suffix)}">
  <div class="ad-slot-label">{esc(label)}</div>
  <ins class="kakao_ad_area"
       style="display:none;"
       data-ad-unit="{esc(unit_id)}"
       data-ad-width="{width}"
       data-ad-height="{height}"></ins>
</div>
""")
        return "".join(blocks)

    dable_widget = DABLE_WIDGETS.get(placement)
    if dable_widget:
        return f"""
<div class="ad-unit ad-slot native-ad-slot" data-ad-unit data-ad-state="pending" data-ad-provider="dable" data-ad-placement="{esc(placement)}">
  <div class="ad-slot-label">{esc(label)}</div>
  <div id="{esc(dable_widget)}"></div>
</div>
"""

    adsense_slot = ADSENSE_UNITS.get(placement)
    if not ADSENSE_CLIENT or not adsense_slot:
        return ""

    return f"""
<div class="ad-unit ad-slot" data-ad-unit data-ad-state="pending" data-ad-provider="adsense" data-ad-placement="{esc(placement)}">
  <div class="ad-slot-label">{esc(label)}</div>
  <ins class="adsbygoogle"
       style="display:block; min-height:{min_height}px"
       data-ssletv-ad="true"
       data-ad-host="{ADSENSE_HOST}"
       data-ad-client="{ADSENSE_CLIENT}"
    data-ad-slot="{esc(adsense_slot)}"
       data-ad-format="auto"
       data-full-width-responsive="true"></ins>
</div>
"""


def sidebar_ads_html(two_units: bool = False) -> str:
    units = [ad_unit_html("광고", 280, "sidebar-top")]
    if two_units:
        units.append(ad_unit_html("광고", 220, "sidebar-bottom"))
    units_html = "".join(unit for unit in units if unit)
    return f'<aside class="ad-rail">{units_html}</aside>' if units_html else ""

def category_widget_html(cat_counts: dict[str, int], active_cat: str | None = None, prefix: str = "") -> str:
    p = prefix + "/" if prefix else ""
    total = sum(cat_counts.values())
    all_cls = " active" if active_cat is None else ""
    rows = [
        f'<li><a href="{p}ssul.html" class="cat-widget-item{all_cls}">전체<span class="cat-count">{total}</span></a></li>'
    ]
    for cat in CATEGORIES:
        slug = SLUG[cat]
        count = cat_counts.get(cat, 0)
        cls = " active" if cat == active_cat else ""
        rows.append(
            f'<li><a href="{p}category-{slug}.html" class="cat-widget-item{cls}">'
            f'{esc(cat)}<span class="cat-count">{count}</span>'
            f'</a></li>'
        )
    rows_html = "".join(rows)
    return (
        f'<nav class="cat-widget">'
        f'<div class="cat-widget-title">카테고리</div>'
        f'<ul class="cat-widget-list">{rows_html}</ul>'
        f'</nav>'
    )


def sidebar_with_cats_html(cat_counts: dict[str, int], active_cat: str | None = None, two_units: bool = False, prefix: str = "") -> str:
    units = [ad_unit_html("광고", 280, "sidebar-top")]
    if two_units:
        units.append(ad_unit_html("광고", 220, "sidebar-bottom"))
    units_html = "".join(unit for unit in units if unit)
    cat_html = category_widget_html(cat_counts, active_cat, prefix)
    return f'<aside class="ad-rail">{cat_html}{units_html}</aside>'


def reading_ad_html() -> str:
    unit = ad_unit_html(placement="article-bottom")
    if not unit:
        return ""
    return unit.replace('class="ad-unit ad-slot"', 'class="ad-unit ad-slot reading-ad"', 1)


def content_ad_html(placement: str) -> str:
    unit = ad_unit_html(placement=placement)
    return f'<div class="content-ad-wrap">{unit}</div>' if unit else ""


def wrap_page(title: str, description: str, canonical: str, body: str, active: str, site_url: str, json_ld: str = "", robots: str = "index,follow,max-image-preview:large", include_ads: bool = True) -> str:
    page_json_ld = json_ld or site_json_ld(site_url)
    ld = f'<script type="application/ld+json">{page_json_ld}</script>'
    ad_scripts = ad_scripts_html(include_ads)
    adsense_meta = f'<meta name="google-adsense-account" content="{ADSENSE_CLIENT}" />' if ADSENSE_CLIENT else ""
    return f"""<!doctype html>
<html lang="ko">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    {verification_meta_html()}
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}" />
    <link rel="canonical" href="{site_url}{canonical}" />
    <meta name="robots" content="{robots}" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="썰TV" />
    <meta property="og:locale" content="ko_KR" />
    <meta property="og:title" content="{esc(title)}" />
    <meta property="og:description" content="{esc(description)}" />
    <meta property="og:url" content="{site_url}{canonical}" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="{esc(title)}" />
    <meta name="twitter:description" content="{esc(description)}" />
    {adsense_meta}
    {shared_head_meta(site_url)}
    <link rel="icon" href="{FAVICON_HREF}" />
    <link rel="stylesheet" href="styles.css?v={ASSET_VERSION}" />
    {ad_scripts}
    {ld}
</head>
<body class="mode-web">
    {header_html(active)}
    {body}
    {footer_html()}
    <button id="mobileWebToggle" class="mobile-web-toggle" type="button">모바일로 보기</button>
    <div class="random-btns" data-index="search-index.json">
        <a id="randomSsulBtn" class="random-post-btn random-ssul" href="#" aria-label="랜덤 썰 보기">
            <span class="random-btn-icon">📜</span>
            <span class="random-btn-label">랜덤 썰</span>
        </a>
        <a id="randomLanovelBtn" class="random-post-btn random-lanovel" href="#" aria-label="랜덤 라노벨">
            <span class="random-btn-icon">🌸</span>
            <span class="random-btn-label">라노벨</span>
        </a>
    </div>
    <script src="app.js?v={ASSET_VERSION}"></script>
</body>
</html>
"""


def write_home(output: Path, ssul_items: list[dict[str, Any]], lanovel_items: list[dict[str, Any]], site_url: str) -> list[str]:
    ssul_sorted = sorted(ssul_items, key=lambda item: parse_date_safe(str(item.get("published_at", ""))), reverse=True)
    lanovel_sorted = sorted(lanovel_items, key=lambda item: parse_date_safe(str(item.get("published_at", ""))), reverse=True)

    cat_chips = "".join(
        f'<a class="cat-chip" href="category-{SLUG[cat]}.html">{esc(cat)}</a>'
        for cat in CATEGORIES
    )
    ssul_cards = "\n".join(ssul_card_html(x) for x in ssul_sorted[:6])
    lanovel_cards = "\n".join(lanovel_card_html(x) for x in lanovel_sorted[:4])

    body = f"""
<div class="site-intro">
  <h1>썰TV 아카이브</h1>
  <p>화제 썰과 라노벨을 한 번에 — 최신순으로 빠르게 탐색</p>
  <div class="cat-chips">{cat_chips}</div>
</div>
<main class="shell">
    <p class="archive-note">썰TV는 흩어진 이야기를 주제별로 정리하고, 원문 출처와 읽기 쉬운 목록을 함께 제공하는 아카이브입니다.</p>
  <section class="home-section">
    <div class="sec-head">
      <h2>최신 썰</h2>
      <a href="ssul.html">전체 {len(ssul_items)}개 보기 →</a>
    </div>
    <div class="post-grid">{ssul_cards}</div>
  </section>
    {content_ad_html("home-between")}
  <section class="home-section">
    <div class="sec-head">
      <h2>최신 라노벨</h2>
      <a href="lanovel.html">전체 {len(lanovel_items)}개 보기 →</a>
    </div>
    <div class="post-grid">{lanovel_cards}</div>
  </section>
</main>
"""
    html_text = wrap_page(
        title="썰TV | 썰/라노벨 아카이브",
        description="화제 썰과 라노벨을 한 번에 탐색하는 아카이브",
        canonical="/",
        body=body,
        active="ssul",
        site_url=site_url,
    )
    (output / "index.html").write_text(html_text, encoding="utf-8")
    return ["index.html"]


def write_ssul_pages(output: Path, items: list[dict[str, Any]], site_url: str, per_page: int) -> list[str]:
    pages = chunked(items, per_page)
    written: list[str] = []
    cat_counts: dict[str, int] = Counter(x.get("category", "기타") for x in items)

    controls_html = "".join(
        f'<a class="cat-chip" href="category-{SLUG[cat]}.html">{esc(cat)}</a>' for cat in CATEGORIES
    )

    for page_no, page_items in enumerate(pages, start=1):
        current_file = list_page_name("ssul", page_no)
        # Paginated pages (2+) are noindex: no SEO value, saves crawl budget
        is_paginated = page_no > 1
        canonical = "/ssul.html" if is_paginated else f"/{current_file}"
        page_robots = "noindex,follow" if is_paginated else "index,follow,max-image-preview:large"
        cards = "\n".join(ssul_card_html(x) for x in page_items) or '<p>표시할 데이터가 없습니다.</p>'
        body = f"""
<main class="shell">
  <div class="page-hero">
    <h1>썰 아카이브</h1>
    <p class="count">전체 {len(items)}개</p>
    <p class="archive-note">카테고리별 경험담을 최신순으로 정리했습니다. 각 글은 원문 출처와 본문을 함께 확인할 수 있습니다.</p>
    <div class="cat-chips">{controls_html}</div>
  </div>
  <div class="layout">
    <div class="content-column">
      <div class="post-grid">{cards}</div>
      {pagination_html("ssul", page_no, len(pages))}
            {content_ad_html("list-bottom")}
    </div>
    {sidebar_with_cats_html(cat_counts, active_cat=None, two_units=True)}
  </div>
</main>
"""
        html_text = wrap_page(
            title="썰TV | 썰 아카이브",
            description="화제 썰 모음 — 카테고리별 최신순 탐색",
            canonical=canonical,
            body=body,
            active="ssul",
            site_url=site_url,
            json_ld=build_json_ld(page_items, site_url, "posts"),
            robots=page_robots,
        )
        (output / current_file).write_text(html_text, encoding="utf-8")
        written.append(current_file)

    return written


def write_category_pages(output: Path, items: list[dict[str, Any]], site_url: str, per_page: int) -> list[str]:
    written: list[str] = []
    cat_counts: dict[str, int] = Counter(x.get("category", "기타") for x in items)
    for category in CATEGORIES:
        slug = SLUG[category]
        category_items = [x for x in items if x.get("category") == category]
        pages = chunked(category_items, per_page)
        for page_no, page_items in enumerate(pages, start=1):
            current_file = list_page_name(f"category-{slug}", page_no)
            is_paginated = page_no > 1
            canonical = f"/category-{slug}.html" if is_paginated else f"/{current_file}"
            page_robots = "noindex,follow" if is_paginated or not category_items else "index,follow,max-image-preview:large"
            cards = "\n".join(ssul_card_html(x) for x in page_items) or '<p>표시할 데이터가 없습니다.</p>'
            category_desc = CATEGORY_DESCRIPTIONS.get(category, f"{category} 카테고리의 최신 글을 정리했습니다.")
            body = f"""
<main class="shell">
  <div class="page-hero">
    <h1>{esc(category)}</h1>
    <p class="count">{len(category_items)}개 · <a href="ssul.html">전체 목록으로</a></p>
    <p class="archive-note">{esc(category_desc)}</p>
  </div>
  <div class="layout">
    <div class="content-column">
      <div class="post-grid">{cards}</div>
      {pagination_html(f"category-{slug}", page_no, len(pages))}
            {content_ad_html("list-bottom")}
    </div>
    {sidebar_with_cats_html(cat_counts, active_cat=category, two_units=True)}
  </div>
</main>
"""
            html_text = wrap_page(
                title=f"썰TV | {category}",
                description=f"{category} 카테고리 모음",
                canonical=canonical,
                body=body,
                active="ssul",
                site_url=site_url,
                json_ld=build_json_ld(page_items, site_url, "posts"),
                robots=page_robots,
            )
            (output / current_file).write_text(html_text, encoding="utf-8")
            if category_items:
                written.append(current_file)

    return written


def write_ssul_post_pages(output: Path, items: list[dict[str, Any]], site_url: str) -> list[str]:
    post_dir = output / "posts"
    ensure(post_dir)
    written: list[str] = []

    for item in items:
        pid = esc(item.get("id", ""))
        title = esc(item.get("title", ""))
        category_name = item.get("category", "기타")
        category_slug = SLUG.get(category_name, "ssul")
        cat = esc(category_name)
        body = item.get("body", "")
        capture_urls = item.get("comment_capture_urls") or []
        source = esc(item.get("source_url", ""))
        date = esc(item.get("published_at", ""))
        modified_date = esc(item.get("updated_at") or item.get("fetched_at") or item.get("published_at", ""))

        raw_excerpt = re.sub(r'\s+', ' ', body).strip()[:160]
        description = esc(raw_excerpt) if raw_excerpt else title
        og_image = esc(media_abs(str(capture_urls[0]), site_url)) if capture_urls else ""

        article_payload = {
            "@type": "Article",
            "headline": item.get("title", ""),
            "description": raw_excerpt if raw_excerpt else item.get("title", ""),
            "url": f"{site_url}/posts/{item.get('id', '')}.html",
            "datePublished": item.get("published_at", ""),
            "dateModified": item.get("updated_at") or item.get("fetched_at") or item.get("published_at", ""),
            "author": {"@type": "Organization", "name": "썰TV"},
            "publisher": {"@id": f"{site_url}/#organization"},
            "inLanguage": "ko-KR",
            "isAccessibleForFree": True,
            "mainEntityOfPage": {"@type": "WebPage", "@id": f"{site_url}/posts/{item.get('id', '')}.html"},
        }
        if capture_urls:
            article_payload["image"] = media_abs(str(capture_urls[0]), site_url)
        breadcrumb_payload = breadcrumb_json_ld(
            site_url,
            [
                ("홈", "/"),
                ("썰 아카이브", "/ssul.html"),
                (category_name, f"/category-{category_slug}.html"),
                (item.get("title", ""), f"/posts/{item.get('id', '')}.html"),
            ],
        )
        article_ld = site_json_ld(site_url, breadcrumb_payload, article_payload)

        related_nav = related_posts_nav(items, item.get("id", ""), limit=5)

        if body:
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
            body_html_parts: list[str] = []
            for para in paragraphs:
                rendered_lines = [linkify_text(line.strip()) for line in para.split("\n") if line.strip()]
                if not rendered_lines:
                    continue
                body_html_parts.append(f"<p>{'<br>'.join(rendered_lines)}</p>")
            body_html = "".join(body_html_parts) or "<p>본문이 없습니다.</p>"
        else:
            body_html = "<p>본문이 없습니다.</p>"

        capture_html = ""
        if capture_urls:
            cards_list: list[str] = []
            for idx, raw_url in enumerate(capture_urls, start=1):
                safe_url = esc(media_src(str(raw_url), ".."))
                cards_list.append(
                    f'<figure class="capture-item">'
                    f'<img src="{safe_url}" loading="lazy" alt="댓글 캡처 {idx}" />'
                    f'<figcaption>댓글 캡처 {idx}</figcaption>'
                    "</figure>"
                )
            capture_html = (
                '<section class="comment-captures">'
                '<h3>댓글 캡처</h3>'
                f'<div class="capture-grid">{"".join(cards_list)}</div>'
                '</section>'
            )

        source_btn = (
            f'<a class="source-btn" href="{source}" rel="nofollow noopener" target="_blank">원문 보기 →</a>'
            if source else ""
        )
        article_is_indexable = is_indexable_ssul(item)
        article_robots = "index,follow,max-image-preview:large" if article_is_indexable else "noindex,follow"
        ad_scripts = ad_scripts_html()
        twitter_card = "summary_large_image" if og_image else "summary"
        twitter_image = f'<meta name="twitter:image" content="{og_image}" />' if og_image else ""

        page = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
    {verification_meta_html()}
  <title>{title} | 썰TV</title>
  <meta name="description" content="{description}" />
  <link rel="canonical" href="{site_url}/posts/{pid}.html" />
    <meta name="robots" content="{article_robots}" />
    <meta property="article:published_time" content="{date}" />
    <meta property="article:modified_time" content="{modified_date}" />
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="썰TV" />
  <meta property="og:locale" content="ko_KR" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  <meta property="og:url" content="{site_url}/posts/{pid}.html" />
  {f'<meta property="og:image" content="{og_image}" />' if og_image else ''}
    <meta name="twitter:card" content="{twitter_card}" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{description}" />
    {twitter_image}
  <meta name="google-adsense-account" content="{ADSENSE_CLIENT}" />
    {shared_head_meta(site_url)}
    <link rel="icon" href="{FAVICON_HREF}" />
    <link rel="stylesheet" href="../styles.css?v={ASSET_VERSION}" />
    {ad_scripts}
  <script type="application/ld+json">{article_ld}</script>
</head>
<body class="mode-web">
  {header_html("ssul", "..")}
  <main class="reading-page">
    <div class="reading-inner">
      <a href="../ssul.html" class="back-link">← 목록으로</a>
      <div class="post-eyebrow">
        <span class="cat-chip">{cat}</span>
        <time>{date}</time>
      </div>
      <h1>{title}</h1>
      <article class="article-body">
        {body_html}
        {capture_html}
      </article>
      {source_btn}
      {reading_ad_html()}
      {related_nav}
    </div>
  </main>
  {footer_html("..")}
  <button id="mobileWebToggle" class="mobile-web-toggle" type="button">모바일로 보기</button>
  <div class="random-btns" data-index="../search-index.json">
    <a id="randomSsulBtn" class="random-post-btn random-ssul" href="#" aria-label="랜덤 썰 보기">
      <span class="random-btn-icon">📜</span>
      <span class="random-btn-label">랜덤 썰</span>
    </a>
    <a id="randomLanovelBtn" class="random-post-btn random-lanovel" href="#" aria-label="랜덤 라노벨">
      <span class="random-btn-icon">🌸</span>
      <span class="random-btn-label">라노벨</span>
    </a>
  </div>
    <script src="../app.js?v={ASSET_VERSION}"></script>
</body>
</html>
"""
        (post_dir / f"{pid}.html").write_text(page, encoding="utf-8")
        if article_is_indexable:
            written.append(f"posts/{pid}.html")

    return written


def write_lanovel_pages(output: Path, items: list[dict[str, Any]], site_url: str, per_page: int) -> list[str]:
    pages = chunked(items, per_page)
    written: list[str] = []

    for page_no, page_items in enumerate(pages, start=1):
        current_file = list_page_name("lanovel", page_no)
        is_paginated = page_no > 1
        canonical = "/lanovel.html" if is_paginated else f"/{current_file}"
        page_robots = "noindex,follow" if is_paginated else "index,follow,max-image-preview:large"
        cards = "\n".join(lanovel_card_html(x) for x in page_items) or '<p>표시할 데이터가 없습니다.</p>'
        body = f"""
<main class="shell">
  <div class="page-hero">
    <h1>라노벨 아카이브</h1>
    <p class="count">전체 {len(items)}개</p>
    <p class="archive-note">작품별 원작 링크, 이미지, 요약 정보를 정리해 새 작품을 빠르게 탐색할 수 있게 구성했습니다.</p>
  </div>
  <div class="layout">
    <div class="content-column">
      <div class="post-grid">{cards}</div>
      {pagination_html("lanovel", page_no, len(pages))}
            {content_ad_html("list-bottom")}
    </div>
    {sidebar_ads_html(two_units=True)}
  </div>
</main>
"""
        html_text = wrap_page(
            title="썰TV | 라노벨 아카이브",
            description="라노벨 정보 모음 — 원작 링크, 이미지, 요약 제공",
            canonical=canonical,
            body=body,
            active="lanovel",
            site_url=site_url,
            json_ld=build_json_ld(page_items, site_url, "lanovel-posts"),
            robots=page_robots,
        )
        (output / current_file).write_text(html_text, encoding="utf-8")
        written.append(current_file)

    return written


def write_lanovel_post_pages(output: Path, items: list[dict[str, Any]], site_url: str) -> list[str]:
    post_dir = output / "lanovel-posts"
    ensure(post_dir)
    written: list[str] = []

    for item in items:
        pid = esc(item.get("id", ""))
        title = esc(item.get("title", ""))
        date = esc(item.get("published_at", ""))
        modified_date = esc(item.get("updated_at") or item.get("fetched_at") or item.get("published_at", ""))
        source = esc(item.get("source_url", ""))
        ncode_url = esc(item.get("ncode_url", ""))
        image_urls = item.get("image_urls") or []
        content_html = lanovel_content_html(item)
        preview_url = ncode_url or source

        raw_synopsis = re.sub(
            r'\s+', ' ', item.get('excerpt', '') or item.get('synopsis', '') or item.get('content', '') or ''
        ).strip()[:160]
        ln_description = esc(raw_synopsis) if raw_synopsis else title
        ln_og_image = esc(media_abs(str(image_urls[0]), site_url)) if image_urls else ""

        ln_article_payload = {
            "@type": "Article",
            "headline": item.get("title", ""),
            "description": raw_synopsis if raw_synopsis else item.get("title", ""),
            "url": f"{site_url}/lanovel-posts/{item.get('id', '')}.html",
            "datePublished": item.get("published_at", ""),
            "dateModified": item.get("updated_at") or item.get("fetched_at") or item.get("published_at", ""),
            "author": {"@type": "Organization", "name": "썰TV"},
            "publisher": {"@id": f"{site_url}/#organization"},
            "inLanguage": "ko-KR",
            "isAccessibleForFree": True,
            "mainEntityOfPage": {"@type": "WebPage", "@id": f"{site_url}/lanovel-posts/{item.get('id', '')}.html"},
        }
        if image_urls:
            ln_article_payload["image"] = media_abs(str(image_urls[0]), site_url)
        ln_breadcrumb_payload = breadcrumb_json_ld(
            site_url,
            [
                ("홈", "/"),
                ("라노벨 아카이브", "/lanovel.html"),
                (item.get("title", ""), f"/lanovel-posts/{item.get('id', '')}.html"),
            ],
        )
        ln_article_ld = site_json_ld(site_url, ln_breadcrumb_payload, ln_article_payload)

        related_nav = related_posts_nav(items, item.get("id", ""), limit=5)

        top_link = (
            f'<a class="cta" href="{preview_url}" rel="nofollow noopener" target="_blank">원작 페이지 바로가기</a>'
            if preview_url else ""
        )
        article_is_indexable = is_indexable_lanovel(item)
        article_robots = "index,follow,max-image-preview:large" if article_is_indexable else "noindex,follow"
        ad_scripts = ad_scripts_html()
        ln_twitter_card = "summary_large_image" if ln_og_image else "summary"
        ln_twitter_image = f'<meta name="twitter:image" content="{ln_og_image}" />' if ln_og_image else ""

        images_html = ""
        if image_urls:
            image_items = []
            for idx, raw_url in enumerate(image_urls, start=1):
                safe_url = esc(media_src(str(raw_url), ".."))
                image_items.append(
                    f'<figure class="lanovel-image-item">'
                    f'<img src="{safe_url}" loading="lazy" alt="{title} 이미지 {idx}" />'
                    "</figure>"
                )
            images_html = f'<section class="lanovel-images">{"".join(image_items)}</section>'

        page = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
    {verification_meta_html()}
  <title>{title} | 라노벨 아카이브</title>
  <meta name="description" content="{ln_description}" />
  <link rel="canonical" href="{site_url}/lanovel-posts/{pid}.html" />
    <meta name="robots" content="{article_robots}" />
    <meta property="article:published_time" content="{date}" />
    <meta property="article:modified_time" content="{modified_date}" />
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="썰TV" />
  <meta property="og:locale" content="ko_KR" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{ln_description}" />
  <meta property="og:url" content="{site_url}/lanovel-posts/{pid}.html" />
  {f'<meta property="og:image" content="{ln_og_image}" />' if ln_og_image else ''}
    <meta name="twitter:card" content="{ln_twitter_card}" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{ln_description}" />
    {ln_twitter_image}
  <meta name="google-adsense-account" content="{ADSENSE_CLIENT}" />
    {shared_head_meta(site_url)}
    <link rel="icon" href="{FAVICON_HREF}" />
    <link rel="stylesheet" href="../styles.css?v={ASSET_VERSION}" />
    {ad_scripts}
  <script type="application/ld+json">{ln_article_ld}</script>
</head>
<body class="mode-web">
  {header_html("lanovel", "..")}
  <main class="reading-page">
    <div class="reading-inner">
      <a href="../lanovel.html" class="back-link">← 라노벨 목록</a>
      <div class="post-eyebrow">
        <span class="cat-chip">라노벨</span>
        <time>{date}</time>
      </div>
      <h1>{title}</h1>
      <article class="article-body">
        <div class="article-top-link">{top_link}</div>
        {images_html}
        {content_html}
      </article>
      {reading_ad_html()}
      {related_nav}
    </div>
  </main>
  {footer_html("..")}
  <button id="mobileWebToggle" class="mobile-web-toggle" type="button">모바일로 보기</button>
  <div class="random-btns" data-index="../search-index.json">
    <a id="randomSsulBtn" class="random-post-btn random-ssul" href="#" aria-label="랜덤 썰 보기">
      <span class="random-btn-icon">📜</span>
      <span class="random-btn-label">랜덤 썰</span>
    </a>
    <a id="randomLanovelBtn" class="random-post-btn random-lanovel" href="#" aria-label="랜덤 라노벨">
      <span class="random-btn-icon">🌸</span>
      <span class="random-btn-label">라노벨</span>
    </a>
  </div>
    <script src="../app.js?v={ASSET_VERSION}"></script>
</body>
</html>
"""
        (post_dir / f"{pid}.html").write_text(page, encoding="utf-8")
        if article_is_indexable:
            written.append(f"lanovel-posts/{pid}.html")

    return written


def support_section_html(title: str, body: str) -> str:
    return f"""
<section class="policy-section">
  <h2>{esc(title)}</h2>
  <p>{esc(body)}</p>
</section>
"""


def support_links_section_html(title: str, links: list[tuple[str, str]], hint: str = "") -> str:
        rows = "".join(
                f'<a class="support-link-btn" href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(name)}</a>'
                for name, url in links
        )
        hint_html = f'<p class="support-link-hint">{esc(hint)}</p>' if hint else ""
        return f"""
<section class="policy-section">
    <h2>{esc(title)}</h2>
    <div class="support-links">{rows}</div>
    {hint_html}
</section>
"""


def toss_qr_section_html() -> str:
    return """
<section class="policy-section">
    <h2>후원 (토스)</h2>
    <div class="support-qr">
        <img src="/assets/brand/toss-qr.png" alt="토스 후원 QR 코드" width="200" height="200" loading="lazy" />
        <p class="support-qr-hint">토스 앱으로 QR을 스캔해 후원할 수 있습니다</p>
    </div>
</section>
"""


def write_support_pages(output: Path, site_url: str) -> list[str]:
    inquiry_mail = mailto_url(
        CONTACT_EMAIL,
        SUPPORT_EMAIL_SUBJECT,
        "요청 유형: (콘텐츠 정정/삭제, 제휴, 광고, 후원)\n페이지 주소: \n상세 내용: ",
    )
    pages = {
        "contact.html": {
            "title": "문의/후원",
            "description": "썰TV 문의 메일과 후원 플랫폼 안내",
            "body": "".join([
                support_links_section_html("문의 메일", [("메일 보내기", inquiry_mail)], f"수신 주소: {CONTACT_EMAIL}"),
                toss_qr_section_html(),
                support_section_html("요청 시 필요한 정보", "글 제목, 페이지 주소, 요청 사유를 함께 보내면 더 빠르게 확인할 수 있습니다."),
                support_section_html("후원금 사용 안내", "후원금은 서버/도메인/이미지 최적화 비용, 신규 아카이브 정리 작업에 우선 사용됩니다."),
            ]),
        },
    }

    written: list[str] = []
    for filename, page_info in pages.items():
        body = f"""
<main class="shell policy-page">
  <div class="page-hero">
    <h1>{esc(page_info["title"])}</h1>
    <p class="archive-note">{esc(page_info["description"])}</p>
  </div>
  <div class="policy-content">{page_info["body"]}</div>
</main>
"""
        html_text = wrap_page(
            title=f"썰TV | {page_info['title']}",
            description=page_info["description"],
            canonical=f"/{filename}",
            body=body,
            active="",
            site_url=site_url,
            include_ads=False,
        )
        (output / filename).write_text(html_text, encoding="utf-8")
        written.append(filename)
    return written


def sitemap_link(path: str, title: str, meta: str = "") -> str:
    meta_html = f'<span class="sitemap-link-meta">{esc(meta)}</span>' if meta else ""
    return (
        "<li>"
        f'<a href="{esc(path)}">'
        f'<span class="sitemap-link-title">{esc(title)}</span>'
        f"{meta_html}"
        "</a>"
        "</li>"
    )


def write_html_sitemap(output: Path, ssul_items: list[dict[str, Any]], lanovel_items: list[dict[str, Any]], site_url: str) -> list[str]:
    main_links = "".join([
        sitemap_link("./", "홈", "최신 글 허브"),
        sitemap_link("ssul.html", "썰 아카이브", f"{len(ssul_items)}개"),
        sitemap_link("lanovel.html", "라노벨 아카이브", f"{len(lanovel_items)}개"),
        sitemap_link("contact.html", "문의/후원", CONTACT_EMAIL),
    ])
    category_links = "".join(
        sitemap_link(f"category-{SLUG[cat]}.html", cat, f"{sum(1 for item in ssul_items if item.get('category') == cat)}개")
        for cat in CATEGORIES
    )

    ssul_sections: list[str] = []
    for category in CATEGORIES:
        category_items = sorted(
            [item for item in ssul_items if item.get("category") == category],
            key=lambda item: parse_date_safe(str(item.get("published_at", ""))),
            reverse=True,
        )
        links = "".join(
            sitemap_link(
                f'posts/{item.get("id", "")}.html',
                str(item.get("title", "")),
                str(item.get("published_at", ""))[:10],
            )
            for item in category_items
            if item.get("id") and is_indexable_ssul(item)
        )
        if links:
            ssul_sections.append(
                f'<section class="sitemap-section"><h2>{esc(category)}</h2><ul class="sitemap-link-list">{links}</ul></section>'
            )

    lanovel_sorted = sorted(
        lanovel_items,
        key=lambda item: parse_date_safe(str(item.get("published_at", ""))),
        reverse=True,
    )
    lanovel_links = "".join(
        sitemap_link(
            f'lanovel-posts/{item.get("id", "")}.html',
            str(item.get("title", "")),
            str(item.get("published_at", ""))[:10],
        )
        for item in lanovel_sorted
        if item.get("id") and is_indexable_lanovel(item)
    )

    body = f"""
<main class="shell sitemap-page">
  <div class="page-hero">
    <h1>사이트맵</h1>
    <p class="archive-note">주요 목록, 카테고리, 색인 가능한 상세 글을 한 페이지에서 따라갈 수 있도록 정리했습니다.</p>
  </div>
  <section class="sitemap-section sitemap-overview">
    <h2>주요 페이지</h2>
    <ul class="sitemap-link-list sitemap-main-list">{main_links}</ul>
  </section>
  <section class="sitemap-section sitemap-overview">
    <h2>썰 카테고리</h2>
    <ul class="sitemap-link-list sitemap-main-list">{category_links}</ul>
  </section>
  <div class="sitemap-columns">
    {''.join(ssul_sections)}
    <section class="sitemap-section"><h2>라노벨 아카이브</h2><ul class="sitemap-link-list">{lanovel_links}</ul></section>
  </div>
</main>
"""
    sitemap_payload = {
        "@type": "CollectionPage",
        "name": "사이트맵",
        "url": f"{site_url}/sitemap.html",
        "description": "썰TV의 주요 페이지와 색인 가능한 글 링크 모음",
        "inLanguage": "ko-KR",
        "isPartOf": {"@id": f"{site_url}/#website"},
    }
    html_text = wrap_page(
        title="썰TV | 사이트맵",
        description="썰TV의 주요 페이지, 카테고리, 상세 글 링크를 정리한 HTML 사이트맵",
        canonical="/sitemap.html",
        body=body,
        active="",
        site_url=site_url,
        json_ld=site_json_ld(site_url, breadcrumb_json_ld(site_url, [("홈", "/"), ("사이트맵", "/sitemap.html")]), sitemap_payload),
        include_ads=False,
    )
    (output / "sitemap.html").write_text(html_text, encoding="utf-8")
    return ["sitemap.html"]


def write_search_index(output: Path, ssul_items: list[dict[str, Any]], lanovel_items: list[dict[str, Any]]) -> None:
    index = []
    for item in ssul_items:
        pid = item.get("id", "")
        title = item.get("title", "")
        excerpt = plain_excerpt(item.get("summary") or item.get("body") or "", title, 100)
        index.append({
            "i": pid,
            "t": title,
            "e": excerpt,
            "c": item.get("category", ""),
            "d": (item.get("published_at") or "")[:10],
            "T": "s",
        })
    for item in lanovel_items:
        pid = item.get("id", "")
        title = item.get("title", "")
        excerpt = lanovel_list_summary(item)
        index.append({
            "i": pid,
            "t": title,
            "e": excerpt,
            "d": (item.get("published_at") or "")[:10],
            "T": "l",
        })
    (output / "search-index.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def write_feed(output: Path, site_url: str, ssul_items: list[dict[str, Any]], lanovel_items: list[dict[str, Any]]) -> None:
    feed_items: list[dict[str, str]] = []
    for item in ssul_items:
        title = str(item.get("title", ""))
        pid = str(item.get("id", ""))
        feed_items.append({
            "title": title,
            "url": f"{site_url}/posts/{pid}.html",
            "id": f"{site_url}/posts/{pid}.html",
            "updated": atom_date(str(item.get("updated_at") or item.get("fetched_at") or item.get("published_at", ""))),
            "published": atom_date(str(item.get("published_at", ""))),
            "summary": plain_excerpt(str(item.get("summary") or item.get("body") or ""), title, 180),
            "category": str(item.get("category", "썰")),
        })
    for item in lanovel_items:
        title = str(item.get("title", ""))
        pid = str(item.get("id", ""))
        feed_items.append({
            "title": title,
            "url": f"{site_url}/lanovel-posts/{pid}.html",
            "id": f"{site_url}/lanovel-posts/{pid}.html",
            "updated": atom_date(str(item.get("updated_at") or item.get("fetched_at") or item.get("published_at", ""))),
            "published": atom_date(str(item.get("published_at", ""))),
            "summary": lanovel_list_summary(item),
            "category": "라노벨",
        })

    feed_items.sort(key=lambda entry: entry["published"], reverse=True)
    latest_items = feed_items[:50]
    feed_updated = latest_items[0]["updated"] if latest_items else atom_date("")

    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        '  <title>썰TV 최신 글</title>',
        f'  <link href="{site_url}/feed.xml" rel="self" type="application/atom+xml" />',
        f'  <link href="{site_url}/" />',
        f'  <id>{site_url}/</id>',
        f'  <updated>{feed_updated}</updated>',
        '  <author><name>썰TV</name></author>',
    ]
    for entry in latest_items:
        xml.extend([
            "  <entry>",
            f'    <title>{esc(entry["title"])}</title>',
            f'    <link href="{esc(entry["url"])}" />',
            f'    <id>{esc(entry["id"])}</id>',
            f'    <published>{entry["published"]}</published>',
            f'    <updated>{entry["updated"]}</updated>',
            f'    <category term="{esc(entry["category"])}" />',
            f'    <summary>{esc(entry["summary"])}</summary>',
            "  </entry>",
        ])
    xml.append("</feed>")
    (output / "feed.xml").write_text("\n".join(xml), encoding="utf-8")


def _write_sub_sitemap(output: Path, filename: str, site_url: str, pages: list[str], date_map: dict[str, str] | None = None) -> None:
    now = datetime.now(UTC).date().isoformat()
    urls = [f"{site_url}/" if p == "index.html" else f"{site_url}/{p}" for p in pages]
    xml = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p, u in zip(pages, urls):
        lastmod = (date_map or {}).get(p, now)[:10] if (date_map or {}).get(p) else now
        xml.append("  <url>")
        xml.append(f"    <loc>{u}</loc>")
        xml.append(f"    <lastmod>{lastmod}</lastmod>")
        xml.append(f"    <changefreq>{sitemap_changefreq(p)}</changefreq>")
        xml.append(f"    <priority>{sitemap_priority(p)}</priority>")
        xml.append("  </url>")
    xml.append("</urlset>")
    (output / filename).write_text("\n".join(xml), encoding="utf-8")


def sitemap_changefreq(path: str) -> str:
    if path in {"index.html", "ssul.html", "lanovel.html"}:
        return "daily"
    if path.startswith(("posts/", "lanovel-posts/")):
        return "monthly"
    return "weekly"


def sitemap_priority(path: str) -> str:
    if path == "index.html":
        return "1.0"
    if path in {"ssul.html", "lanovel.html"}:
        return "0.9"
    if path == "sitemap.html":
        return "0.6"
    if path.startswith(("posts/", "lanovel-posts/")):
        return "0.8"
    if path.startswith("category-"):
        return "0.7"
    return "0.5"


def write_sitemap(output: Path, site_url: str, pages: list[str], date_map: dict[str, str] | None = None) -> None:
    now = datetime.now(UTC).date().isoformat()

    # Exclude paginated listing pages (page 2+) — they are noindex and waste crawl budget
    listing_pages = [
        p for p in pages
        if not p.startswith("posts/") and not p.startswith("lanovel-posts/")
        and "-page-" not in p
    ]
    ssul_pages = [p for p in pages if p.startswith("posts/")]
    lanovel_pages = [p for p in pages if p.startswith("lanovel-posts/")]

    subs: list[str] = []
    if listing_pages:
        _write_sub_sitemap(output, "sitemap-listing.xml", site_url, listing_pages)
        subs.append("sitemap-listing.xml")
    if ssul_pages:
        _write_sub_sitemap(output, "sitemap-ssul.xml", site_url, ssul_pages, date_map)
        subs.append("sitemap-ssul.xml")
    if lanovel_pages:
        _write_sub_sitemap(output, "sitemap-lanovel.xml", site_url, lanovel_pages, date_map)
        subs.append("sitemap-lanovel.xml")

    idx = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for s in subs:
        idx.append("  <sitemap>")
        idx.append(f"    <loc>{site_url}/{s}</loc>")
        idx.append(f"    <lastmod>{now}</lastmod>")
        idx.append("  </sitemap>")
    idx.append("</sitemapindex>")
    (output / "sitemap.xml").write_text("\n".join(idx), encoding="utf-8")


def write_robots(output: Path, site_url: str) -> None:
    (output / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n",
        encoding="utf-8",
    )


def copy_assets(output: Path, assets_dir: Path) -> None:
    (output / "styles.css").write_text((assets_dir / "styles.css").read_text(encoding="utf-8"), encoding="utf-8")
    (output / "app.js").write_text((assets_dir / "app.js").read_text(encoding="utf-8"), encoding="utf-8")
    (output / "favicon.svg").write_text(FAVICON_SVG, encoding="utf-8")
    (output / "site.webmanifest").write_text(site_manifest_json(), encoding="utf-8")
    (output / "sw.js").write_text(service_worker_js(), encoding="utf-8")
    for gv in assets_dir.glob("google*.html"):
        (output / gv.name).write_text(gv.read_text(encoding="utf-8"), encoding="utf-8")
    media_dir = Path("assets")
    if media_dir.exists():
        target_media = output / "assets"
        if target_media.exists():
            shutil.rmtree(target_media)
        shutil.copytree(media_dir, target_media)
    favicon_ico = Path("assets/brand/favicon.ico")
    if favicon_ico.exists():
        shutil.copyfile(favicon_ico, output / "favicon.ico")
    root_ads = Path("ads.txt")
    if root_ads.exists():
        (output / "ads.txt").write_text(root_ads.read_text(encoding="utf-8"), encoding="utf-8")


def load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="JSON 데이터로 SEO 정적 사이트를 생성합니다.")
    parser.add_argument("--data", default="data/posts.json")
    parser.add_argument("--lanovel-data", default="data/lanovel_posts.json")
    parser.add_argument("--assets", default="site")
    parser.add_argument("--out", default="dist")
    parser.add_argument("--site-url", default=INDEX_SITE_URL)
    parser.add_argument("--per-page", type=int, default=DEFAULT_PER_PAGE)
    parser.add_argument("--lanovel-per-page", type=int, default=6)
    args = parser.parse_args()

    out = Path(args.out)
    ensure(out)
    site_url = args.site_url.rstrip("/")

    raw_ssul = load_json(Path(args.data))
    ssul_items = [x for x in raw_ssul if x.get("category") in CATEGORIES]
    lanovel_items = load_json(Path(args.lanovel_data))

    copy_assets(out, Path(args.assets))
    write_search_index(out, ssul_items, lanovel_items)
    write_feed(out, site_url, ssul_items, lanovel_items)

    # Build date map: post path → actual publication date (for sitemap lastmod)
    date_map: dict[str, str] = {}
    for item in ssul_items:
        pid = item.get("id", "")
        pub = (item.get("published_at") or "")[:10]
        if pid and pub:
            date_map[f"posts/{pid}.html"] = pub
    for item in lanovel_items:
        pid = item.get("id", "")
        pub = (item.get("published_at") or "")[:10]
        if pid and pub:
            date_map[f"lanovel-posts/{pid}.html"] = pub

    all_pages: list[str] = []
    all_pages.extend(write_home(out, ssul_items, lanovel_items, site_url))
    all_pages.extend(write_support_pages(out, site_url))
    all_pages.extend(write_html_sitemap(out, ssul_items, lanovel_items, site_url))
    all_pages.extend(write_ssul_pages(out, ssul_items, site_url, max(1, args.per_page)))
    all_pages.extend(write_category_pages(out, ssul_items, site_url, max(1, args.per_page)))
    all_pages.extend(write_ssul_post_pages(out, ssul_items, site_url))
    all_pages.extend(write_lanovel_pages(out, lanovel_items, site_url, max(1, args.lanovel_per_page)))
    all_pages.extend(write_lanovel_post_pages(out, lanovel_items, site_url))

    write_sitemap(out, site_url, all_pages, date_map)
    write_robots(out, site_url)

    print(f"built ssul={len(ssul_items)}, lanovel={len(lanovel_items)} to {out}")


if __name__ == "__main__":
    main()