import argparse
import hashlib
import json
import random
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_CATEGORIES = [
    "군대 썰",
    "육아 썰",
    "연애/결혼 썰",
    "직장/사회 썰",
    "학교/학원 썰",
    "가족/친척 썰",
    "공포/사건 썰",
    "기타 화제 썰",
]

TITLE_SELECTORS = [
    ".post-title",
    "h1.post-title",
    ".entry-title",
    "h1",
    ".title",
]
BODY_SELECTORS = [
    "article .post-content",
    "#post-body",
    ".post-content",
    ".entry-content",
    ".content",
    "article",
]
DATE_SELECTORS = [
    ".publish-date",
    ".post-date",
    "time",
    ".date",
    ".entry-date",
]


@dataclass
class ScrapeConfig:
    category_url: str
    target_count: int
    sleep_seconds: float
    timeout_seconds: int
    output_path: Path


def clean_text(text: str) -> str:
    """Remove extra whitespace and normalize text."""
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def classify_category(title: str, body: str) -> str:
    """Auto-classify article into one of 8 categories based on keywords."""
    combined = f"{title} {body}".upper()
    
    if re.search(r"군대|훈련소|부대|상병|하사|전역|병장|병역|징집|기간|군인|자대|전투", combined):
        return "군대 썰"
    elif re.search(r"육아|아이|아기|아들|딸|엄마|아버지|어린이|아이디|아플|기저귀|젖병|예방접종|어린아이|위험", combined):
        return "육아 썰"
    elif re.search(r"연애|결혼|남자|여자|여친|남친|헤어|이혼|신랑|신부|배우자|짝|사귀|키스|고백|사랑|외도|바람|데이트", combined):
        return "연애/결혼 썰"
    elif re.search(r"직장|회사|상사|동료|업무|퇴근|출근|월급|연봉|승진|좌천|인사|부서|동료|직원|직업|사직|고용|해고", combined):
        return "직장/사회 썰"
    elif re.search(r"학교|학생|친구|선배|후배|학폭|따돌림|수학|영어|시험|입시|대학|고등학교|중학교|초등학교|교사|선생님", combined):
        return "학교/학원 썰"
    elif re.search(r"부모|형|언니|오빠|누나|동생|할아버지|할머니|아버지|어머니|가족|친척|삼촌|이모|조상|상속", combined):
        return "가족/친척 썰"
    elif re.search(r"무섭|공포|죽음|귀신|유령|호러|사건|범죄|살인|사고|위험|공포|놀라|두려|섬뜩|끔찍", combined):
        return "공포/사건 썰"
    else:
        return "기타 화제 썰"


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


def fetch_html(session: requests.Session, url: str, timeout: int) -> str:
    """Fetch HTML from URL with retries."""
    for attempt in range(3):
        try:
            res = session.get(url, timeout=timeout)
            if res.status_code == 200:
                return res.text
        except requests.RequestException as e:
            if attempt < 2:
                time.sleep(1)
            continue
    return ""


def extract_article_links(html: str, base_url: str) -> list[str]:
    """Extract all article links from category page."""
    soup = BeautifulSoup(html, "lxml")
    links = []
    
    # Try common article link selectors
    selectors = [
        "article a",
        ".post-link a",
        ".entry-link a",
        ".card a",
        "a.post-title",
        ".title a",
    ]
    
    for selector in selectors:
        for elem in soup.select(selector):
            href = elem.get("href", "").strip()
            if href and "entry" in href.lower():
                # Make absolute URL
                if href.startswith("http"):
                    links.append(href)
                elif href.startswith("/"):
                    links.append(urljoin(base_url, href))
                else:
                    links.append(urljoin(base_url, "/" + href))
    
    # Deduplicate
    return list(dict.fromkeys(links))


def extract_article_title(soup: BeautifulSoup) -> str:
    """Extract article title."""
    for selector in TITLE_SELECTORS:
        elem = soup.select_one(selector)
        if elem:
            text = clean_text(elem.get_text(" "))
            if text and len(text) > 5:
                return text[:200]
    return ""


def extract_article_body(soup: BeautifulSoup) -> str:
    """Extract full article body content."""
    for selector in BODY_SELECTORS:
        elem = soup.select_one(selector)
        if elem:
            # Remove unwanted elements
            for tag in elem.select("script, style, .comments, .comment, .ad, .advertisement"):
                tag.decompose()
            
            text = clean_text(elem.get_text(" "))
            if text and len(text) > 50:
                return text
    
    return ""


def extract_article_date(soup: BeautifulSoup) -> str:
    """Extract article publication date."""
    for selector in DATE_SELECTORS:
        elem = soup.select_one(selector)
        if elem:
            text = clean_text(elem.get_text(" "))
            # Try to extract ISO date
            match = re.search(
                r"(\d{4})[.-/](\d{1,2})[.-/](\d{1,2})",
                text
            )
            if match:
                year, month, day = match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    return datetime.now(UTC).strftime("%Y-%m-%d")


def parse_article(html: str, article_url: str) -> dict | None:
    """Parse full article content from HTML."""
    soup = BeautifulSoup(html, "lxml")
    
    title = extract_article_title(soup)
    body = extract_article_body(soup)
    
    if not title or not body:
        return None
    
    category = classify_category(title, body)
    published_at = extract_article_date(soup)
    
    # Create summary from first ~260 chars
    summary = body[:260] + ("..." if len(body) > 260 else "")
    
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
        "body": body,  # FULL CONTENT
        "fetched_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }


def scrape(config: ScrapeConfig) -> list[dict]:
    """Scrape full article content from category page."""
    session = build_session()
    
    print(f"[1/3] Fetching category page: {config.category_url}")
    html = fetch_html(session, config.category_url, config.timeout_seconds)
    if not html:
        print("[ERROR] Failed to fetch category page")
        return []
    
    print(f"[2/3] Extracting article links...")
    article_links = extract_article_links(html, config.category_url)
    article_links = article_links[:config.target_count]
    print(f"[OK] Found {len(article_links)} articles")
    
    collected = []
    seen_ids = set()
    
    print(f"[3/3] Scraping article content ({len(article_links)} articles)...")
    for idx, article_url in enumerate(article_links, start=1):
        article_html = fetch_html(session, article_url, config.timeout_seconds)
        if not article_html:
            print(f"  [{idx}/{len(article_links)}] SKIP (fetch failed)")
            continue
        
        article = parse_article(article_html, article_url)
        if not article:
            print(f"  [{idx}/{len(article_links)}] SKIP (parse failed)")
            continue
        
        if article["id"] in seen_ids:
            print(f"  [{idx}/{len(article_links)}] SKIP (duplicate)")
            continue
        
        seen_ids.add(article["id"])
        collected.append(article)
        
        body_preview = article["body"][:60].replace("\n", " ") + "..."
        print(f"  [{idx}/{len(article_links)}] OK: {article['title'][:40]} | {article['category']}")
        
        # Polite rate limiting
        time.sleep(config.sleep_seconds + random.random() * 0.5)
    
    return collected


def merge_with_existing(new_items: list[dict], existing_path: Path) -> list[dict]:
    """Merge new items with existing posts, avoiding duplicates."""
    existing = []
    if existing_path.exists():
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
    
    existing_ids = {item["id"] for item in existing}
    
    merged = existing.copy()
    added_count = 0
    for item in new_items:
        if item["id"] not in existing_ids:
            merged.append(item)
            added_count += 1
    
    print(f"[MERGE] Existing: {len(existing)}, New: {len(new_items)}, Added: {added_count}, Total: {len(merged)}")
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "ssletv.com 카테고리에서 기사를 수집하고 "
            "각 기사의 전체 본문 내용을 저장합니다."
        )
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="수집할 카테고리 URL (예: https://www.ssletv.com/category/썰%%20전용%%20모음소)"
    )
    parser.add_argument("--target-count", type=int, default=100)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--output", type=str, default="data/posts.json")
    parser.add_argument("--merge", action="store_true", help="기존 데이터와 병합")
    
    args = parser.parse_args()
    
    config = ScrapeConfig(
        category_url=args.url,
        target_count=max(1, args.target_count),
        sleep_seconds=max(0.2, args.sleep),
        timeout_seconds=max(5, args.timeout),
        output_path=Path(args.output),
    )
    
    print("[START] Full content scraping...")
    items = scrape(config)
    
    if not items:
        print("[ERROR] No items collected")
        return
    
    output_path = config.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if args.merge and output_path.exists():
        merged = merge_with_existing(items, output_path)
        output_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    else:
        output_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    print(f"[DONE] Wrote {len(items)} items -> {output_path}")


if __name__ == "__main__":
    main()
