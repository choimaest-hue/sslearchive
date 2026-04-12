import json
import time
import random
import re
import hashlib
from pathlib import Path
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


CATEGORY_URL = "https://www.ssletv.com/category/%EC%8D%B0%20%EC%A0%84%EC%9A%A9%20%EB%AA%A8%EC%9D%8C%EC%86%8C"

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
            
            text = elem.get_text(" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            
            if text and len(text) > 200:
                return text
    
    # Fallback: try to get text from body minus header/footer
    body = soup.find('body')
    if body:
        # Remove common non-content elements
        for tag in body.select("header, footer, nav, script, style, .header, .footer, .sidebar, .nav, .ads"):
            tag.decompose()
        text = body.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if text and len(text) > 500:
            return text
    
    return ""


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
                return res.text
        except requests.RequestException:
            if attempt < 2:
                time.sleep(1)
    return ""


def extract_article_links(html: str) -> list[str]:
    """Extract all article links from category page."""
    soup = BeautifulSoup(html, "lxml")
    links = []
    
    # Find all list_content > a.link_post elements
    for elem in soup.select("div.list_content a.link_post"):
        href = elem.get("href", "").strip()
        if href:
            # Convert to full URL if relative
            if href.startswith("/"):
                full_url = urljoin(CATEGORY_URL, href)
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = urljoin(CATEGORY_URL, "/" + href)
            links.append(full_url)
    
    # Deduplicate
    return list(dict.fromkeys(links))


def extract_article_title(html: str) -> str:
    """Extract article title."""
    soup = BeautifulSoup(html, "lxml")
    
    # Try multiple selectors to find title
    selectors = [
        "h1",
        ".entry-title", 
        "h1.entry-title",
        ".post-title",
        "h1.post-title",
        "strong.tit_post",
        "title",
        ".title",
        ".tt_article_title",
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text().strip()
            if text and len(text) > 3 and len(text) < 500:
                return text[:200]
    
    # Fallback: look in meta tags
    for elem in soup.select("meta[property='og:title']"):
        content = elem.get("content", "").strip()
        if content and len(content) > 3:
            return content[:200]
    
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
    title = extract_article_title(html)
    body = extract_full_body(html)
    
    if not title or not body:
        return None
    
    category = classify_category(title, body)
    published_at = extract_article_date(html)
    
    # Create summary from first ~260 chars
    summary = body[:260] + ("..." if len(body) > 260 else "")
    
    # Create excerpt from first ~1000 chars
    excerpt = body[:1000]
    
    # Generate unique ID
    article_id = f"ssul-{hashlib.sha1(article_url.encode()).hexdigest()[:12]}"
    
    return {
        "id": article_id,
        "title": title,
        "source_url": article_url,
        "source_site": "ssletv",
        "published_at": published_at,
        "category": category,
        "summary": summary,
        "excerpt": excerpt,
        "body": body,
        "comments": [],
        "comment_count": 0,
        "fetched_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }


def scrape_all() -> list[dict]:
    """
    1. Fetch category page
    2. Extract all article links
    3. Visit each link and collect full content
    """
    session = build_session()
    
    print("[1/4] Fetching category page...")
    html = fetch_html(session, CATEGORY_URL)
    if not html:
        print("[ERROR] Failed to fetch category page")
        return []
    
    print("[2/4] Extracting article links...")
    article_links = extract_article_links(html)
    print(f"[OK] Found {len(article_links)} articles")
    
    if not article_links:
        print("[ERROR] No articles found")
        return []
    
    print("[3/4] Fetching full content from articles...")
    collected = []
    seen_ids = set()
    
    for idx, article_url in enumerate(article_links, start=1):
        article_html = fetch_html(session, article_url)
        if not article_html:
            print(f"  [{idx}/{len(article_links)}] FAIL (fetch)")
            continue
        
        article = parse_article(article_html, article_url)
        if not article:
            print(f"  [{idx}/{len(article_links)}] FAIL (parse)")
            continue
        
        if article["id"] in seen_ids:
            print(f"  [{idx}/{len(article_links)}] SKIP (duplicate)")
            continue
        
        seen_ids.add(article["id"])
        collected.append(article)
        
        # Print progress with title preview
        title_preview = article["title"][:50]
        cat = article["category"]
        body_len = len(article["body"])
        print(f"  [{idx}/{len(article_links)}] ✓ {title_preview} | {cat} | {body_len} chars")
        
        # Polite rate limiting
        time.sleep(0.9 + random.random() * 0.4)
    
    print("[4/4] Collection complete!")
    print(f"\n[RESULT] Collected {len(collected)} articles total")
    return collected


def main() -> None:
    print("=" * 80)
    print("썰 모음 카테고리 - 전체 본문 수집")
    print("=" * 80)
    
    items = scrape_all()
    
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
    
    print(f"\n✓ Saved {len(items)} articles to {output_path}")
    
    # Print statistics
    from collections import Counter
    cat_counts = Counter([item["category"] for item in items])
    print("\n[카테고리별 통계]")
    for cat in CATEGORIES:
        count = cat_counts.get(cat, 0)
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
