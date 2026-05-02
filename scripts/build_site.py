import argparse
import html
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
ADSENSE_CLIENT = "ca-pub-3397494907696633"
ADSENSE_HOST = "ca-host-pub-9691043933427338"
CONTACT_EMAIL = "choimaest@naver.com"
MIN_INDEXABLE_TEXT_CHARS = 300
FAVICON_HREF = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%23c0392b'/%3E%3Ctext x='32' y='41' font-size='34' text-anchor='middle' fill='white' font-family='Arial,sans-serif'%3ES%3C/text%3E%3C/svg%3E"

# Optional ad network hooks. Leave empty until each network issues real IDs.
KAKAO_ADFIT_UNITS: dict[str, tuple[str, int, int]] = {}
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
    idx_path = f"{prefix}/search-index.json" if prefix else "search-index.json"
    return f"""
<header class="site-header">
  <div class="site-header-inner">
    <a href="{p}index.html" class="brand">썰TV</a>
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
    <a href="{p}about.html">소개</a>
    <span>·</span>
    <a href="{p}privacy.html">개인정보처리방침</a>
    <span>·</span>
    <a href="{p}contact.html">문의</a>
    <span>·</span>
    <span>© 2025 썰TV</span>
  </div>
</footer>
"""


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
    thumb = esc((item.get("image_urls") or [""])[0])
    ncode_url = esc(item.get("ncode_url", ""))

    thumb_html = f'<img class="lanovel-thumb" src="{thumb}" alt="{title}" loading="lazy" />' if thumb else ""
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
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": elements,
    }
    return json.dumps(payload, ensure_ascii=False)


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


def ad_unit_html(label: str, min_height: int = 250, placement: str = "sidebar") -> str:
    kakao_unit = KAKAO_ADFIT_UNITS.get(placement)
    if kakao_unit:
        unit_id, width, height = kakao_unit
        return f"""
<div class="ad-unit ad-slot" data-ad-unit data-ad-state="pending" data-ad-provider="kakao" data-ad-placement="{esc(placement)}">
  <div class="ad-slot-label">{esc(label)}</div>
  <ins class="kakao_ad_area"
       style="display:none;"
       data-ad-unit="{esc(unit_id)}"
       data-ad-width="{width}"
       data-ad-height="{height}"></ins>
</div>
"""

    dable_widget = DABLE_WIDGETS.get(placement)
    if dable_widget:
        return f"""
<div class="ad-unit ad-slot native-ad-slot" data-ad-unit data-ad-state="pending" data-ad-provider="dable" data-ad-placement="{esc(placement)}">
  <div class="ad-slot-label">{esc(label)}</div>
  <div id="{esc(dable_widget)}"></div>
</div>
"""

    if not ADSENSE_CLIENT:
        return ""

    return f"""
<div class="ad-unit ad-slot" data-ad-unit data-ad-state="pending" data-ad-provider="adsense" data-ad-placement="{esc(placement)}">
  <div class="ad-slot-label">{esc(label)}</div>
  <ins class="adsbygoogle"
       style="display:block; min-height:{min_height}px"
       data-ssletv-ad="true"
       data-ad-host="{ADSENSE_HOST}"
       data-ad-client="{ADSENSE_CLIENT}"
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
    unit = ad_unit_html("광고", 200, "article-bottom")
    if not unit:
        return ""
    return unit.replace('class="ad-unit ad-slot"', 'class="ad-unit reading-ad"', 1)


def wrap_page(title: str, description: str, canonical: str, body: str, active: str, site_url: str, json_ld: str = "", robots: str = "index,follow,max-image-preview:large", include_ads: bool = True) -> str:
    ld = f'<script type="application/ld+json">{json_ld}</script>' if json_ld else ""
    ad_scripts = ad_scripts_html(include_ads)
    return f"""<!doctype html>
<html lang="ko">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="naver-site-verification" content="36275f7ef596c60eff1322aa781657cefd4a75f9" />
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
    <meta name="google-adsense-account" content="{ADSENSE_CLIENT}" />
    <link rel="icon" href="{FAVICON_HREF}" />
    <link rel="stylesheet" href="styles.css" />
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
    <script src="app.js"></script>
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
    </div>
    {sidebar_with_cats_html(cat_counts, active_cat=category)}
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
        cat = esc(item.get("category", "기타"))
        body = item.get("body", "")
        capture_urls = item.get("comment_capture_urls") or []
        source = esc(item.get("source_url", ""))
        date = esc(item.get("published_at", ""))

        raw_excerpt = re.sub(r'\s+', ' ', body).strip()[:160]
        description = esc(raw_excerpt) if raw_excerpt else title
        og_image = esc(str(capture_urls[0])) if capture_urls else ""

        article_payload = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": item.get("title", ""),
            "description": raw_excerpt if raw_excerpt else item.get("title", ""),
            "url": f"{site_url}/posts/{item.get('id', '')}.html",
            "datePublished": item.get("published_at", ""),
            "publisher": {"@type": "Organization", "name": "썰TV"},
            "mainEntityOfPage": {"@type": "WebPage", "@id": f"{site_url}/posts/{item.get('id', '')}.html"},
        }
        if capture_urls:
            article_payload["image"] = str(capture_urls[0])
        article_ld = json.dumps(article_payload, ensure_ascii=False)

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
                safe_url = esc(str(raw_url))
                cards_list.append(
                    f'<a class="capture-item" href="{safe_url}" target="_blank" rel="nofollow noopener">'
                    f'<img src="{safe_url}" loading="lazy" alt="댓글 캡처 {idx}" />'
                    f'<span>댓글 캡처 {idx}</span>'
                    "</a>"
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

        page = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="naver-site-verification" content="36275f7ef596c60eff1322aa781657cefd4a75f9" />
  <title>{title} | 썰TV</title>
  <meta name="description" content="{description}" />
  <link rel="canonical" href="{site_url}/posts/{pid}.html" />
    <meta name="robots" content="{article_robots}" />
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="썰TV" />
  <meta property="og:locale" content="ko_KR" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  <meta property="og:url" content="{site_url}/posts/{pid}.html" />
  {f'<meta property="og:image" content="{og_image}" />' if og_image else ''}
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{description}" />
  <meta name="google-adsense-account" content="{ADSENSE_CLIENT}" />
    <link rel="icon" href="{FAVICON_HREF}" />
  <link rel="stylesheet" href="../styles.css" />
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
  <script src="../app.js"></script>
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
    </div>
    {sidebar_ads_html()}
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
        source = esc(item.get("source_url", ""))
        ncode_url = esc(item.get("ncode_url", ""))
        image_urls = item.get("image_urls") or []
        content_html = lanovel_content_html(item)
        preview_url = ncode_url or source

        raw_synopsis = re.sub(r'\s+', ' ', item.get('synopsis', '') or '').strip()[:160]
        ln_description = esc(raw_synopsis) if raw_synopsis else title
        ln_og_image = esc(str(image_urls[0])) if image_urls else ""

        ln_article_payload = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": item.get("title", ""),
            "description": raw_synopsis if raw_synopsis else item.get("title", ""),
            "url": f"{site_url}/lanovel-posts/{item.get('id', '')}.html",
            "datePublished": item.get("published_at", ""),
            "publisher": {"@type": "Organization", "name": "썰TV"},
            "mainEntityOfPage": {"@type": "WebPage", "@id": f"{site_url}/lanovel-posts/{item.get('id', '')}.html"},
        }
        if image_urls:
            ln_article_payload["image"] = str(image_urls[0])
        ln_article_ld = json.dumps(ln_article_payload, ensure_ascii=False)

        related_nav = related_posts_nav(items, item.get("id", ""), limit=5)

        top_link = (
            f'<a class="cta" href="{preview_url}" rel="nofollow noopener" target="_blank">원작 페이지 바로가기</a>'
            if preview_url else ""
        )
        article_is_indexable = is_indexable_lanovel(item)
        article_robots = "index,follow,max-image-preview:large" if article_is_indexable else "noindex,follow"
        ad_scripts = ad_scripts_html()

        images_html = ""
        if image_urls:
            image_items = []
            for idx, raw_url in enumerate(image_urls[:12], start=1):
                safe_url = esc(raw_url)
                image_items.append(
                    f'<a href="{safe_url}" target="_blank" rel="nofollow noopener">'
                    f'<img src="{safe_url}" loading="lazy" alt="{title} 이미지 {idx}" />'
                    "</a>"
                )
            images_html = f'<section class="lanovel-images">{"".join(image_items)}</section>'

        page = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="naver-site-verification" content="36275f7ef596c60eff1322aa781657cefd4a75f9" />
  <title>{title} | 라노벨 아카이브</title>
  <meta name="description" content="{ln_description}" />
  <link rel="canonical" href="{site_url}/lanovel-posts/{pid}.html" />
    <meta name="robots" content="{article_robots}" />
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="썰TV" />
  <meta property="og:locale" content="ko_KR" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{ln_description}" />
  <meta property="og:url" content="{site_url}/lanovel-posts/{pid}.html" />
  {f'<meta property="og:image" content="{ln_og_image}" />' if ln_og_image else ''}
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{ln_description}" />
  <meta name="google-adsense-account" content="{ADSENSE_CLIENT}" />
    <link rel="icon" href="{FAVICON_HREF}" />
  <link rel="stylesheet" href="../styles.css" />
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
  <script src="../app.js"></script>
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


def write_support_pages(output: Path, site_url: str) -> list[str]:
    pages = {
        "about.html": {
            "title": "썰TV 소개",
            "description": "썰TV 아카이브의 운영 목적, 콘텐츠 구성, 출처 표기 원칙 안내",
            "body": "".join([
                support_section_html("운영 목적", "썰TV는 온라인에서 흩어진 썰과 라노벨 정보를 주제별로 정리해 빠르게 탐색할 수 있도록 만든 아카이브입니다."),
                support_section_html("콘텐츠 구성", "각 글은 제목, 카테고리, 발행일, 본문 또는 요약, 원문 링크를 중심으로 구성됩니다. 목록과 검색 인덱스는 사용자가 원하는 주제를 찾기 쉽도록 생성됩니다."),
                support_section_html("출처와 문의", f"원문 확인이 필요한 글에는 출처 링크를 표시합니다. 정정, 삭제, 제휴 문의는 {CONTACT_EMAIL}로 연락할 수 있습니다."),
            ]),
        },
        "privacy.html": {
            "title": "개인정보처리방침",
            "description": "썰TV의 개인정보 처리, 쿠키, 광고 파트너, 문의 방법 안내",
            "body": "".join([
                support_section_html("개인정보 수집", "썰TV는 정적 페이지 기반 사이트이며 회원가입, 댓글 작성, 결제 기능을 제공하지 않습니다. 사이트 자체에서 이름, 연락처, 계정 정보를 직접 수집하지 않습니다."),
                support_section_html("쿠키와 광고", "Google AdSense, Kakao AdFit, Dable 같은 광고 또는 분석 파트너를 사용할 수 있으며, 해당 파트너는 광고 제공과 부정 사용 방지를 위해 쿠키나 유사 기술을 사용할 수 있습니다."),
                support_section_html("외부 링크", "글 원문, 작품 페이지, 광고 링크처럼 외부 사이트로 이동하는 링크가 포함될 수 있습니다. 외부 사이트의 개인정보 처리 방식은 각 서비스의 정책을 따릅니다."),
                support_section_html("문의", f"개인정보, 콘텐츠 정정, 광고 관련 문의는 {CONTACT_EMAIL} 메일로 연락해 주세요."),
            ]),
        },
        "contact.html": {
            "title": "문의",
            "description": "썰TV 콘텐츠 정정, 삭제, 광고, 제휴 문의 안내",
            "body": "".join([
                support_section_html("연락처", f"콘텐츠 정정, 삭제, 광고, 제휴 문의는 {CONTACT_EMAIL} 메일로 연락해 주세요."),
                support_section_html("요청 시 필요한 정보", "글 제목, 페이지 주소, 요청 사유를 함께 보내면 더 빠르게 확인할 수 있습니다."),
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


def _write_sub_sitemap(output: Path, filename: str, site_url: str, pages: list[str], date_map: dict[str, str] | None = None) -> None:
    now = datetime.now(UTC).date().isoformat()
    urls = [f"{site_url}/" if p == "index.html" else f"{site_url}/{p}" for p in pages]
    xml = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p, u in zip(pages, urls):
        lastmod = (date_map or {}).get(p, now)[:10] if (date_map or {}).get(p) else now
        xml.append("  <url>")
        xml.append(f"    <loc>{u}</loc>")
        xml.append(f"    <lastmod>{lastmod}</lastmod>")
        xml.append("  </url>")
    xml.append("</urlset>")
    (output / filename).write_text("\n".join(xml), encoding="utf-8")


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
    for gv in assets_dir.glob("google*.html"):
        (output / gv.name).write_text(gv.read_text(encoding="utf-8"), encoding="utf-8")
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
    parser.add_argument("--site-url", default="https://ssletv.com")
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