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
    """
    깔끔한 페이지네이션: 현재 페이지 +/- 2개, 맨앞, 맨뒤만 표시
    """
    if total <= 1:
        return ""

    numbers = []
    
    # 표시할 페이지 범위 계산: 현재 페이지 ±2
    start = max(1, current - 2)
    end = min(total, current + 2)
    
    # 첫 페이지 (항상 표시 또는 범위에 포함 시 생략)
    if start > 1:
        cls = "page-link"
        numbers.append(f'<a class="{cls}" href="{list_page_name(base, 1)}">1</a>')
        if start > 2:
            numbers.append('<span class="page-ellipsis">···</span>')
    
    # 현재 페이지 주변 번호들
    for page in range(start, end + 1):
        cls = "page-link current" if page == current else "page-link"
        numbers.append(f'<a class="{cls}" href="{list_page_name(base, page)}">{page}</a>')
    
    # 마지막 페이지 (항상 표시 또는 범위에 포함 시 생략)
    if end < total:
        if end < total - 1:
            numbers.append('<span class="page-ellipsis">···</span>')
        cls = "page-link"
        numbers.append(f'<a class="{cls}" href="{list_page_name(base, total)}">{total}</a>')

    return (
        '<nav class="pagination" aria-label="페이지 이동">'
        f"{''.join(numbers)}"
        "</nav>"
    )


def header_html(active: str) -> str:
    ssul_cls = "main-nav-link active" if active == "ssul" else "main-nav-link"
    lanovel_cls = "main-nav-link active" if active == "lanovel" else "main-nav-link"
    return f"""
<header class="site-header">
  <div class="site-header-inner">
    <a href="index.html" class="brand">썰TV</a>
    <nav class="main-nav" aria-label="메인 주제">
      <a href="ssul.html" class="{ssul_cls}">썰 아카이브</a>
      <a href="lanovel.html" class="{lanovel_cls}">라노벨 아카이브</a>
    </nav>
  </div>
</header>
"""


def footer_html() -> str:
    return """
<footer class="site-footer">
  <div class="footer-grid">
    <section>
      <h4>사이트 소개</h4>
      <p>썰TV는 이야기형 콘텐츠를 주제별로 정리해 읽기 쉽게 제공하는 아카이브입니다.</p>
    </section>
    <section>
      <h4>콘텐츠 주제</h4>
      <p><a href="ssul.html">썰 아카이브</a> · <a href="lanovel.html">라노벨 아카이브</a></p>
    </section>
    <section>
      <h4>광고 문의</h4>
      <p><a href="mailto:choimaest@naver.com">choimaest@naver.com</a></p>
    </section>
  </div>
</footer>
"""


def ssul_card_html(item: dict[str, Any]) -> str:
  title = esc(item.get("title", ""))
  summary = esc(item.get("summary", ""))
  cat = esc(item.get("category", "기타"))
  pid = esc(item.get("id", ""))
  date = esc(item.get("published_at", ""))
  comments = int(item.get("comment_count") or 0)
  source = esc(item.get("source_url", ""))
  return (
    f'<article class="card" data-category="{cat}">'
    f"<h3><a href=\"posts/{pid}.html\">{title}</a></h3>"
    f"<p>{summary}</p>"
    f'<div class="meta"><span>{cat}</span><span>{date} · 댓글 {comments}</span></div>'
    f'<p class="source-line">출처: <a href="{source}" rel="nofollow noopener" target="_blank">원문 보기</a></p>'
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
    f'<p class="source-line">원작 링크: <a href="{ncode_url}" rel="nofollow noopener" target="_blank">바로가기</a></p>'
    if ncode_url
    else ""
  )
  return (
    '<article class="card card-compact">'
    f"{thumb_html}"
    f"<h3><a href=\"lanovel-posts/{pid}.html\">{title}</a></h3>"
    f"<p class=\"preview-summary\">요약: {summary}</p>"
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
    """
    현재 글의 앞뒤로 관련 글들을 표시합니다.
    limit은 앞/뒤 몇 개씩 표시할지입니다.
    """
    try:
        current_idx = next(i for i, item in enumerate(items) if item.get("id") == current_id)
    except StopIteration:
        return ""
    
    prev_items = items[max(0, current_idx - limit):current_idx]
    next_items = items[current_idx + 1:min(len(items), current_idx + 1 + limit)]
    
    # 이전글/다음글 네비게이션
    nav_html = ""
    prev_post = prev_items[-1] if prev_items else None
    next_post = next_items[0] if next_items else None
    
    if prev_post or next_post:
        nav_html += '<section class="prev-next-nav">'
        if prev_post:
            prev_title = esc(prev_post.get("title", ""))
            prev_id = esc(prev_post.get("id", ""))
            nav_html += f'<a href="{prev_id}.html" class="prev-next-item"><span class="prev-next-label">← 이전글</span><span class="prev-next-title">{prev_title}</span></a>'
        else:
            nav_html += '<div style="opacity: 0.3;"></div>'
        
        if next_post:
            next_title = esc(next_post.get("title", ""))
            next_id = esc(next_post.get("id", ""))
            nav_html += f'<a href="{next_id}.html" class="prev-next-item"><span class="prev-next-label">다음글 →</span><span class="prev-next-title">{next_title}</span></a>'
        else:
            nav_html += '<div style="opacity: 0.3;"></div>'
        nav_html += '</section>'
    
    # 관련 글 목록 (이전/다음 제외)
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
            nav_html += f'<a href="{pid}.html" class="related-post"><span class="related-cat">{cat}</span><span class="related-title">{title}</span></a>'
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


def wrap_page(title: str, description: str, canonical: str, body: str, active: str, site_url: str, json_ld: str = "") -> str:
    ld = f'<script type="application/ld+json">{json_ld}</script>' if json_ld else ""
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="naver-site-verification" content="36275f7ef596c60eff1322aa781657cefd4a75f9" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}" />
  <link rel="canonical" href="{site_url}{canonical}" />
  <meta name="robots" content="index,follow,max-image-preview:large" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="썰TV" />
  <meta property="og:locale" content="ko_KR" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(description)}" />
  <meta property="og:url" content="{site_url}{canonical}" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{esc(title)}" />
  <meta name="twitter:description" content="{esc(description)}" />
  <link rel="stylesheet" href="styles.css" />
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3397494907696633"
     crossorigin="anonymous"></script>
  {ld}
</head>
<body class="mode-web">
  {header_html(active)}
  {body}
  {footer_html()}
  <button id="mobileWebToggle" class="mobile-web-toggle" type="button">모바일로 보기</button>
  <script src="app.js"></script>
</body>
</html>
"""


def write_home(output: Path, ssul_items: list[dict[str, Any]], lanovel_items: list[dict[str, Any]], site_url: str) -> list[str]:
    body = f"""
<main class="top-shell">
  <section class="hero">
    <h1>썰/라노벨 아카이브</h1>
    <p class="subtitle">읽기 중심 UX로 구성한 2개 메인 주제형 아카이브</p>
    <div class="badges">
      <span class="badge">썰 {len(ssul_items)}개</span>
      <span class="badge">라노벨 {len(lanovel_items)}개</span>
      <span class="badge">페이지당 10개</span>
    </div>
  </section>
  <section class="topic-grid">
    <article class="topic-card">
      <h3>썰 아카이브</h3>
      <p>군대, 육아, 연애/결혼, 직장/사회 중심의 화제 썰 탐색</p>
      <a class="cta" href="ssul.html">썰 보러가기</a>
    </article>
    <article class="topic-card">
      <h3>라노벨 아카이브</h3>
      <p>라노벨 정보 카테고리 게시글 원문 기반 정리</p>
      <a class="cta" href="lanovel.html">라노벨 보러가기</a>
    </article>
  </section>
</main>
"""
    html_text = wrap_page(
        title="썰TV | 썰/라노벨 아카이브",
        description="썰과 라노벨을 주제별로 모아 읽기 쉽게 제공하는 아카이브",
        canonical="/",
        body=body,
        active="ssul",
        site_url=site_url,
    )
    (output / "index.html").write_text(html_text, encoding="utf-8")
    return ["index.html"]


def write_ssul_pages(output: Path, items: list[dict[str, Any]], site_url: str, per_page: int) -> list[str]:
    pages = chunked(items, per_page)
    counter = Counter([x.get("category", "기타") for x in items])
    written: list[str] = []
    badges_html = "".join(
        f'<span class="badge">{esc(cat.replace(" 썰", ""))} {counter.get(cat, 0)}</span>' for cat in CATEGORIES
    )
    controls_html = "".join(
        f'<a class="filter-btn" href="category-{SLUG[cat]}.html">{esc(cat)}</a>' for cat in CATEGORIES
    )

    for page_no, page_items in enumerate(pages, start=1):
        current_file = list_page_name("ssul", page_no)
        canonical = f"/{current_file}"
        cards = "\n".join(ssul_card_html(x) for x in page_items) or '<p class="panel">표시할 데이터가 없습니다.</p>'
        body = f"""
<main class="top-shell">
  <section class="hero">
    <h1>썰 아카이브</h1>
    <p class="subtitle">카테고리별로 정리된 썰 데이터 목록</p>
    <p class="subtitle">페이지 {page_no} / {len(pages)}</p>
    <div class="badges">
      <span class="badge">총 {len(items)}개</span>
      {badges_html}
    </div>
  </section>
  <section class="controls">
    {controls_html}
  </section>
  <section class="layout">
    <div class="grid">{cards}</div>
    <aside class="sidebar">
      <div class="panel ad-slot">광고 영역 A (300x250)</div>
      <div class="panel ad-slot">광고 영역 B (반응형)</div>
    </aside>
  </section>
  {pagination_html("ssul", page_no, len(pages))}
</main>
"""
        html_text = wrap_page(
            title="썰TV | 썰 아카이브",
            description="썰 카테고리 기반 목록",
            canonical=canonical,
            body=body,
            active="ssul",
            site_url=site_url,
            json_ld=build_json_ld(page_items, site_url, "posts"),
        )
        (output / current_file).write_text(html_text, encoding="utf-8")
        written.append(current_file)

    return written


def write_category_pages(output: Path, items: list[dict[str, Any]], site_url: str, per_page: int) -> list[str]:
    written: list[str] = []
    for category in CATEGORIES:
        slug = SLUG[category]
        category_items = [x for x in items if x.get("category") == category]
        pages = chunked(category_items, per_page)
        for page_no, page_items in enumerate(pages, start=1):
            current_file = list_page_name(f"category-{slug}", page_no)
            canonical = f"/{current_file}"
            cards = "\n".join(ssul_card_html(x) for x in page_items) or '<p class="panel">표시할 데이터가 없습니다.</p>'
            body = f"""
<main class="top-shell">
  <section class="hero">
    <h1>{esc(category)}</h1>
    <p class="subtitle">총 {len(category_items)}개</p>
    <p class="subtitle">페이지 {page_no} / {len(pages)}</p>
    <p><a href="ssul.html">썰 전체 목록으로</a></p>
  </section>
  <section class="layout">
    <div class="grid">{cards}</div>
    <aside class="sidebar">
      <div class="panel ad-slot">광고 영역</div>
    </aside>
  </section>
  {pagination_html(f"category-{slug}", page_no, len(pages))}
</main>
"""
            html_text = wrap_page(
                title=f"썰TV | {category}",
                description=f"{category} 카테고리 목록",
                canonical=canonical,
                body=body,
                active="ssul",
                site_url=site_url,
                json_ld=build_json_ld(page_items, site_url, "posts"),
            )
            (output / current_file).write_text(html_text, encoding="utf-8")
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

        # SEO: body excerpt for meta description
        raw_excerpt = re.sub(r'\s+', ' ', body).strip()[:160]
        description = esc(raw_excerpt) if raw_excerpt else title

        # SEO: first comment capture image for og:image
        og_image = esc(str(capture_urls[0])) if capture_urls else ""

        # SEO: Article JSON-LD
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
        
        # 관련 글 네비게이션 (앞뒤로 5개씩)
        related_nav = related_posts_nav(items, item.get("id", ""), limit=5)

        # Convert body to paragraph blocks and preserve in-paragraph line breaks.
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
          cards: list[str] = []
          for idx, raw_url in enumerate(capture_urls, start=1):
            safe_url = esc(str(raw_url))
            cards.append(
              f'<a class="capture-item" href="{safe_url}" target="_blank" rel="nofollow noopener">'
              f'<img src="{safe_url}" loading="lazy" alt="댓글 캡처 {idx}" />'
              f'<span>댓글 캡처 {idx}</span>'
              "</a>"
            )
          capture_html = (
            '<section class="comment-captures">'
            '<h3>댓글 캡처</h3>'
            f'<div class="capture-grid">{"".join(cards)}</div>'
            '</section>'
          )

        page = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="naver-site-verification" content="36275f7ef596c60eff1322aa781657cefd4a75f9" />
  <title>{title} | 썰TV</title>
  <meta name="description" content="{description}" />
  <link rel="canonical" href="{site_url}/posts/{pid}.html" />
  <meta name="robots" content="index,follow,max-image-preview:large" />
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
  <link rel="stylesheet" href="../styles.css" />
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3397494907696633"
     crossorigin="anonymous"></script>
  <script type="application/ld+json">{article_ld}</script>
</head>
<body class="mode-web">
  <header class="site-header">
    <div class="site-header-inner">
      <a href="../index.html" class="brand">썰TV</a>
      <nav class="main-nav"><a href="../ssul.html" class="main-nav-link active">썰 아카이브</a><a href="../lanovel.html" class="main-nav-link">라노벨 아카이브</a></nav>
    </div>
  </header>
  <main class="top-shell">
    <section class="hero">
      <h1>{title}</h1>
      <p class="subtitle">{cat} · {date}</p>
      <div class="nav-panel">
        <a href="../ssul.html" class="nav-btn secondary">← 목록으로</a>
        <a href="{source}" rel="nofollow noopener" target="_blank" class="nav-btn">📖 원문 보기</a>
      </div>
    </section>
    <section class="layout">
      <article class="panel article-body">
          {body_html}
          {capture_html}
      </article>
      <aside class="sidebar"><div class="panel ad-slot">광고 영역</div></aside>
    </section>
    {related_nav}
  </main>
  {footer_html()}
  <button id="mobileWebToggle" class="mobile-web-toggle" type="button">모바일로 보기</button>
  <script src="../app.js"></script>
</body>
</html>
"""
        (post_dir / f"{pid}.html").write_text(page, encoding="utf-8")
        written.append(f"posts/{pid}.html")

    return written


def write_lanovel_pages(output: Path, items: list[dict[str, Any]], site_url: str, per_page: int) -> list[str]:
    pages = chunked(items, per_page)
    written: list[str] = []

    for page_no, page_items in enumerate(pages, start=1):
        current_file = list_page_name("lanovel", page_no)
        canonical = f"/{current_file}"
        cards = "\n".join(lanovel_card_html(x) for x in page_items) or '<p class="panel">표시할 데이터가 없습니다.</p>'
        body = f"""
<main class="top-shell">
  <section class="hero">
    <h1>라노벨 아카이브</h1>
    <p class="subtitle">사용자 사이트 원문 기반 라노벨 정보 페이지</p>
    <p class="subtitle">페이지 {page_no} / {len(pages)}</p>
    <div class="badges"><span class="badge">총 {len(items)}개</span><span class="badge">페이지당 {per_page}개</span></div>
  </section>
  <section class="layout">
    <div class="grid lanovel-grid">{cards}</div>
    <aside class="sidebar">
      <div class="panel ad-slot">광고 영역</div>
    </aside>
  </section>
  {pagination_html("lanovel", page_no, len(pages))}
</main>
"""
        html_text = wrap_page(
            title="썰TV | 라노벨 아카이브",
            description="라노벨 정보 전용 목록",
            canonical=canonical,
            body=body,
            active="lanovel",
            site_url=site_url,
            json_ld=build_json_ld(page_items, site_url, "lanovel-posts"),
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

        # SEO: description from synopsis or title
        raw_synopsis = re.sub(r'\s+', ' ', item.get('synopsis', '') or '').strip()[:160]
        ln_description = esc(raw_synopsis) if raw_synopsis else title

        # SEO: first image for og:image
        ln_og_image = esc(str(image_urls[0])) if image_urls else ""

        # SEO: Article JSON-LD
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
        
        # 관련 글 네비게이션 (앞뒤로 5개씩)
        related_nav = related_posts_nav(items, item.get("id", ""), limit=5)

        top_link = (
          f'<a class="cta" href="{preview_url}" rel="nofollow noopener" target="_blank">원작 페이지 바로가기</a>'
          if preview_url
          else ""
        )

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
  <meta name="robots" content="index,follow,max-image-preview:large" />
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
  <link rel="stylesheet" href="../styles.css" />
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3397494907696633"
     crossorigin="anonymous"></script>
  <script type="application/ld+json">{ln_article_ld}</script>
</head>
<body class="mode-web">
  <header class="site-header">
    <div class="site-header-inner">
      <a href="../index.html" class="brand">썰TV</a>
      <nav class="main-nav"><a href="../ssul.html" class="main-nav-link">썰 아카이브</a><a href="../lanovel.html" class="main-nav-link active">라노벨 아카이브</a></nav>
    </div>
  </header>
  <main class="top-shell">
    <section class="hero">
      <h1>{title}</h1>
      <p class="subtitle">{date}</p>
      <div class="nav-panel">
        <a href="../lanovel.html" class="nav-btn secondary">← 라노벨 목록</a>
        <a href="{source}" rel="nofollow noopener" target="_blank" class="nav-btn">📖 원문 페이지</a>
      </div>
    </section>
    <section class="layout">
      <article class="panel article-body"><div class="article-top-link">{top_link}</div>{images_html}{content_html}</article>
      <aside class="sidebar"><div class="panel ad-slot">광고 영역</div></aside>
    </section>
    {related_nav}
  </main>
  {footer_html()}
  <button id="mobileWebToggle" class="mobile-web-toggle" type="button">모바일로 보기</button>
  <script src="../app.js"></script>
</body>
</html>
"""
        (post_dir / f"{pid}.html").write_text(page, encoding="utf-8")
        written.append(f"lanovel-posts/{pid}.html")

    return written


def _write_sub_sitemap(output: Path, filename: str, site_url: str, pages: list[str]) -> None:
    now = datetime.now(UTC).date().isoformat()
    urls = [f"{site_url}/" if p == "index.html" else f"{site_url}/{p}" for p in pages]
    xml = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append("  <url>")
        xml.append(f"    <loc>{u}</loc>")
        xml.append(f"    <lastmod>{now}</lastmod>")
        xml.append("  </url>")
    xml.append("</urlset>")
    (output / filename).write_text("\n".join(xml), encoding="utf-8")


def write_sitemap(output: Path, site_url: str, pages: list[str]) -> None:
    now = datetime.now(UTC).date().isoformat()

    # Split pages into sub-sitemaps
    listing_pages = [p for p in pages if not p.startswith("posts/") and not p.startswith("lanovel-posts/")]
    ssul_pages = [p for p in pages if p.startswith("posts/")]
    lanovel_pages = [p for p in pages if p.startswith("lanovel-posts/")]

    subs: list[str] = []
    if listing_pages:
        _write_sub_sitemap(output, "sitemap-listing.xml", site_url, listing_pages)
        subs.append("sitemap-listing.xml")
    if ssul_pages:
        _write_sub_sitemap(output, "sitemap-ssul.xml", site_url, ssul_pages)
        subs.append("sitemap-ssul.xml")
    if lanovel_pages:
        _write_sub_sitemap(output, "sitemap-lanovel.xml", site_url, lanovel_pages)
        subs.append("sitemap-lanovel.xml")

    # Write sitemap index
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
    # Google Search Console verification files
    for gv in assets_dir.glob("google*.html"):
        (output / gv.name).write_text(gv.read_text(encoding="utf-8"), encoding="utf-8")


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

    all_pages: list[str] = []
    all_pages.extend(write_home(out, ssul_items, lanovel_items, site_url))
    all_pages.extend(write_ssul_pages(out, ssul_items, site_url, max(1, args.per_page)))
    all_pages.extend(write_category_pages(out, ssul_items, site_url, max(1, args.per_page)))
    all_pages.extend(write_ssul_post_pages(out, ssul_items, site_url))
    all_pages.extend(write_lanovel_pages(out, lanovel_items, site_url, max(1, args.lanovel_per_page)))
    all_pages.extend(write_lanovel_post_pages(out, lanovel_items, site_url))

    write_sitemap(out, site_url, all_pages)
    write_robots(out, site_url)

    print(f"built ssul={len(ssul_items)}, lanovel={len(lanovel_items)} to {out}")


if __name__ == "__main__":
    main()
