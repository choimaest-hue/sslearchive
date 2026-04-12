import json
import time
import random
import re
import hashlib
from pathlib import Path
from datetime import UTC, datetime
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, UnicodeDammit


BASE_CATEGORY_URL = "https://www.ssletv.com/category/%EC%8D%B0%20%EC%A0%84%EC%9A%A9%20%EB%AA%A8%EC%9D%8C%EC%86%8C"

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

GENERIC_TITLE_PATTERNS = [
    re.compile(r"세상\s*모든\s*잡동사니\s*집합소", re.IGNORECASE),
    re.compile(r"스레\s*TV|썰\s*TV|SSLETV", re.IGNORECASE),
]


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _is_generic_title(text: str) -> bool:
    value = _normalize_spaces(text)
    if not value:
        return True
    return any(pattern.search(value) for pattern in GENERIC_TITLE_PATTERNS)


def _clean_title(text: str) -> str:
    value = _normalize_spaces(text)
    # 흔한 사이트명 접미사 정리
    value = re.sub(r"\s*\|\s*세상\s*모든\s*잡동사니\s*집합소\s*스레\s*TV\s*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*\|\s*SSLETV\s*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*-\s*세상\s*모든\s*잡동사니\s*집합소\s*스레\s*TV\s*$", "", value, flags=re.IGNORECASE)
    return value[:200]


def _title_from_url(article_url: str) -> str:
    path = urlparse(article_url).path.strip("/")
    if not path:
        return ""
    slug = path.split("/")[-1]
    if slug.startswith("entry/"):
        slug = slug.split("entry/", 1)[-1]
    slug = slug.replace("+", " ")
    slug = unquote(slug)
    slug = slug.replace("-", " ")
    slug = re.sub(r"\s+", " ", slug).strip()
    return _clean_title(slug)


def _extract_paragraph_texts(container: BeautifulSoup) -> list[str]:
    # br을 줄바꿈으로 치환해 원문 엔터를 살린다.
    for br in container.select("br"):
        br.replace_with("\n")

    block_selectors = [
        "p", "li", "blockquote", "pre", "h2", "h3", "h4", "figcaption",
        "div.txc-textbox", "div[data-ke-type='text']",
    ]

    paragraphs: list[str] = []
    seen: set[str] = set()

    for sel in block_selectors:
        for node in container.select(sel):
            text = node.get_text("\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = "\n".join(line.rstrip() for line in text.split("\n"))
            text = text.strip()
            if not text:
                continue
            if len(text) < 2:
                continue
            if text in seen:
                continue
            seen.add(text)
            paragraphs.append(text)

    if paragraphs:
        return paragraphs

    # 블록 태그가 없으면 컨테이너 전체 텍스트를 줄단위로 살린다.
    fallback = container.get_text("\n", strip=True)
    fallback = re.sub(r"\n{3,}", "\n\n", fallback).strip()
    if not fallback:
        return []
    return [chunk.strip() for chunk in fallback.split("\n\n") if chunk.strip()]


def classify_category(title: str, body: str) -> str:
    """Auto-classify article into one of 8 categories based on keywords."""
    combined = f"{title} {body}".upper()
    
    if re.search(r"군대|훈련소|부대|상병|하사|전역|병장|병역|징집|기간|군인|자대|전투", combined):
        return "군대 썰"
    elif re.search(r"육아|아이|아기|아들|딸|엄마|아버지|어린이|아이디|아플|기저귀|젖병|예방접종|어린아이|위험", combined):
        return "육아 썰"
    elif re.search(r"연애|결혼|남자|여자|여친|남친|헤어|이혼|신랑|신부|배우자|짝|사귀|키스|고백|사랑|외도|바람|데이트", combined):
        return "연애/결혼 썰"
    elif re.search(r"직장|회사|상사|동료|업무|퇴근|출근|월급|연봉|승진|좌천|인사|부서|직원|직업|사직|고용|해고", combined):
        return "직장/사회 썰"
    elif re.search(r"학교|학생|친구|선배|후배|학폭|따돌림|수학|영어|시험|입시|대학|고등학교|중학교|초등학교|교사|선생님", combined):
        return "학교/학원 썰"
    elif re.search(r"부모|형|언니|오빠|누나|동생|할아버지|할머니|아버지|어머니|가족|친척|삼촌|이모|조상|상속", combined):
        return "가족/친척 썰"
    elif re.search(r"무섭|공포|죽음|귀신|유령|호러|사건|범죄|살인|사고|위험|놀라|두려|섬뜩|끔찍", combined):
        return "공포/사건 썰"
    else:
        return "기타 화제 썰"


def extract_full_body(html: str) -> str:
    """Extract full article body from HTML."""
    soup = BeautifulSoup(html, "lxml")
    
    # Try multiple selectors to find body content
    selectors = [
        "div.se-main-container",
        "div.post-content",
        "article .view-content",
        "div.article-content",
        "div.entry-content",
        "div.content-view",
        "div#postViewArea",
        "div.tt_article_useless_p_margin",
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            # Remove script, style, and ad elements
            for tag in elem.select("script, style, .ads, .advertisement, .comments, .reply"):
                tag.decompose()

            paragraphs = _extract_paragraph_texts(elem)
            text = "\n\n".join(paragraphs).strip()

            if text and len(text) > 60:
                return text
    
    # Fallback: try to get text from body minus header/footer
    body = soup.find('body')
    if body:
        # Remove common non-content elements
        for tag in body.select("header, footer, nav, script, style, .header, .footer, .sidebar, .nav, .ads"):
            tag.decompose()

        paragraphs = _extract_paragraph_texts(body)
        text = "\n\n".join(paragraphs).strip()
        if text and len(text) > 120:
            return text
    
    # 최종 fallback: 문장 단위로 너무 짧은 노이즈만 제거하고 반환
    fallback_text = soup.get_text("\n", strip=True)
    fallback_text = re.sub(r"\n{3,}", "\n\n", fallback_text).strip()
    if len(fallback_text) > 80:
        return fallback_text

    return ""


def extract_capture_image_urls(html: str, article_url: str) -> list[str]:
    """Extract image URLs from article content area (used for comment capture linking)."""
    soup = BeautifulSoup(html, "lxml")
    selectors = [
        "div.se-main-container",
        "div.post-content",
        "article .view-content",
        "div.article-content",
        "div.entry-content",
        "div.content-view",
        "div#postViewArea",
        "div.tt_article_useless_p_margin",
    ]

    candidates: list[str] = []
    containers = []
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            containers.append(elem)

    if not containers and soup.body:
        containers = [soup.body]

    for container in containers:
        for img in container.select("img, source"):
            raw = (
                img.get("data-src")
                or img.get("data-original")
                or img.get("data-lazy-src")
                or img.get("src")
                or ""
            ).strip()

            if not raw:
                srcset = (img.get("srcset") or "").strip()
                if srcset:
                    raw = srcset.split(",")[0].strip().split(" ")[0]

            if not raw or raw.startswith("data:"):
                continue

            full = urljoin(article_url, raw)
            if full.startswith("http"):
                candidates.append(full)

    # de-duplicate preserving order
    return list(dict.fromkeys(candidates))


def build_session() -> requests.Session:
    """Create a session with proper headers."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }
    )
    return session


def fetch_html(session: requests.Session, url: str, timeout: int = 15) -> str:
    """Fetch HTML from URL with retries."""
    for attempt in range(3):
        try:
            res = session.get(url, timeout=timeout)
            if res.status_code == 200:
                content = res.content
                declared = (res.encoding or "").lower()

                # 서버가 UTF 계열을 선언하면 이를 신뢰한다.
                if "utf" in declared:
                    return content.decode("utf-8", errors="replace")

                if declared in {"cp949", "euc-kr", "ks_c_5601-1987"}:
                    codec = "cp949" if declared == "ks_c_5601-1987" else declared
                    return content.decode(codec, errors="replace")

                # 선언이 없거나 부정확하면 BeautifulSoup의 인코딩 추정기를 사용한다.
                dammit = UnicodeDammit(content, is_html=True)
                if dammit.unicode_markup:
                    return dammit.unicode_markup

                # 최종 fallback
                return content.decode("utf-8", errors="replace")

            if res.status_code in {403, 429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(1.5 + random.random() * 2.0)
                continue
        except requests.RequestException:
            if attempt < 2:
                time.sleep(1)
    return ""


def extract_article_links_from_page(html: str) -> list[str]:
    """Extract all article links from a single category page."""
    soup = BeautifulSoup(html, "lxml")
    links = []
    
    # Find all list_content > a.link_post elements
    for elem in soup.select("div.list_content a.link_post"):
        href = elem.get("href", "").strip()
        if href:
            # Convert to full URL if relative
            if href.startswith("/"):
                full_url = urljoin(BASE_CATEGORY_URL, href)
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = urljoin(BASE_CATEGORY_URL, "/" + href)
            links.append(full_url)
    
    # Deduplicate
    return list(dict.fromkeys(links))


def extract_article_title(html: str, article_url: str = "") -> str:
    """Extract article title."""
    soup = BeautifulSoup(html, "lxml")

    # 우선순위: og:title -> <title> -> article title 계열 -> h1/h2/h3
    candidates: list[str] = []

    og = soup.select_one("meta[property='og:title']")
    if og and og.get("content"):
        candidates.append(og.get("content", ""))

    if soup.title:
        candidates.append(soup.title.get_text(" ", strip=True))

    selectors = [
        "strong.tit_post",
        ".entry-title",
        "h1.entry-title",
        ".post-title",
        "h1.post-title",
        ".tt_article_title",
        "article h1",
        "article h2",
        "h1",
        "h2",
        "h3",
    ]
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            candidates.append(elem.get_text(" ", strip=True))

    for raw in candidates:
        cleaned = _clean_title(raw)
        if 3 <= len(cleaned) <= 200 and not _is_generic_title(cleaned):
            return cleaned

    # fallback 1: generic이라도 첫 후보 반환
    for raw in candidates:
        cleaned = _clean_title(raw)
        if 3 <= len(cleaned) <= 200:
            return cleaned

    # fallback 2: URL slug 기반 제목 복원
    from_url = _title_from_url(article_url)
    if 3 <= len(from_url) <= 200 and not _is_generic_title(from_url):
        return from_url

    return ""


def extract_article_date(html: str) -> str:
    """Extract article publication date."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text()
    
    # Try to find date pattern
    match = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    return datetime.now(UTC).strftime("%Y-%m-%d")


def parse_article(html: str, article_url: str) -> dict | None:
    """Parse full article content from HTML."""
    title = extract_article_title(html, article_url)
    if not title:
        title = _title_from_url(article_url)
    body = extract_full_body(html)
    capture_urls = extract_capture_image_urls(html, article_url)
    
    if not title or not body:
        return None
    
    category = classify_category(title, body)
    published_at = extract_article_date(html)
    
    # Generate unique ID
    article_id = f"ssul-{hashlib.sha1(article_url.encode()).hexdigest()[:12]}"
    
    return {
        "id": article_id,
        "title": title,
        "source_url": article_url,
        "source_site": "ssletv",
        "published_at": published_at,
        "category": category,
        "body": body,
        "comment_capture_urls": capture_urls,
        "comments": [],
        "comment_count": 0,
        "fetched_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }


def scrape_all_pages(max_pages: int = 500) -> list[dict]:
    """
    Scrape all pages of the category:
    1. Fetch each category page (page=1, page=2, ...)
    2. Extract all article links
    3. Visit each link and collect full content
    """
    session = build_session()
    
    all_links: list[str] = []
    collected = []
    seen_ids = set()
    seen_links: set[str] = set()
    
    print("[1/5] Fetching all category pages...")
    print("=" * 80)
    
    # Fetch all pages
    for page_num in range(1, max_pages + 1):
        if page_num == 1:
            category_url = BASE_CATEGORY_URL
        else:
            category_url = f"{BASE_CATEGORY_URL}?page={page_num}"
        
        print(f"[페이지 {page_num}] 가져오는 중...", end=" ")
        html = fetch_html(session, category_url)
        
        if not html:
            print("[ERR] 실패 (fetch error)")
            break
        
        # Extract links from this page
        page_links = extract_article_links_from_page(html)
        if not page_links:
            print("[DONE] 링크 없음 (collection complete)")
            break
        
        new_links = [link for link in page_links if link not in seen_links]
        if not new_links:
            print("[DONE] 새 링크 없음 (pagination end)")
            break

        for link in new_links:
            seen_links.add(link)
            all_links.append(link)

        print(f"[OK] {len(new_links)}개 신규 링크 발견 (누계: {len(all_links)})")
        
        time.sleep(0.5 + random.random() * 0.4)
    
    print("=" * 80)
    print(f"\n[2/5] 총 {len(all_links)}개 기사 링크 확보\n")
    
    if not all_links:
        print("[ERROR] No articles found")
        return []
    
    print("[3/5] 기사 본문 수집 시작...")
    print("=" * 80)
    
    for idx, article_url in enumerate(all_links, start=1):
        article_html = fetch_html(session, article_url)
        if not article_html:
            print(f"[{idx}/{len(all_links)}] [ERR] FAIL (fetch)")
            continue
        
        article = parse_article(article_html, article_url)
        if not article:
            print(f"[{idx}/{len(all_links)}] [ERR] FAIL (parse)")
            continue
        
        if article["id"] in seen_ids:
            print(f"[{idx}/{len(all_links)}] [SKIP] duplicate")
            continue
        
        seen_ids.add(article["id"])
        collected.append(article)
        
        # Print progress at intervals to avoid overwhelming output.
        if idx <= 20 or idx % 25 == 0 or idx == len(all_links):
            title_preview = article["title"][:45]
            cat = article["category"].replace(" 썰", "")
            body_len = len(article["body"])
            print(f"[{idx}/{len(all_links)}] [OK] {title_preview:<50} | {cat:<10} | {body_len:>5} chars")
        
        # Polite rate limiting
        time.sleep(0.8 + random.random() * 0.4)
    
    print("=" * 80)
    print(f"\n[4/5] 수집 완료! {len(collected)}/{len(all_links)} 기사 성공\n")
    
    return collected


def main() -> None:
    print("\n")
    print("=" * 80)
    print("썰 모음 카테고리 - 전체 페이지 크롤링 및 본문 수집")
    print("=" * 80)
    print()
    
    items = scrape_all_pages(max_pages=500)
    
    if not items:
        print("[ERROR] No items collected")
        return
    
    # Save to posts.json (replacing existing data)
    output_path = Path("data/posts.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    output_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print(f"[5/5] 저장 완료!")
    print("=" * 80)
    print(f"[OK] {len(items)}개 기사를 {output_path}에 저장했습니다\n")
    
    # Print statistics
    from collections import Counter
    cat_counts = Counter([item["category"] for item in items])
    print("[카테고리별 통계]")
    for cat in CATEGORIES:
        count = cat_counts.get(cat, 0)
        if count > 0:
            print(f"  {cat}: {count}")
    print()


if __name__ == "__main__":
    main()
