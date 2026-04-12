import json
import time
import random
import re
from pathlib import Path
from datetime import UTC, datetime

import requests
from bs4 import BeautifulSoup


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


def extract_full_body(html: str) -> str:
    """Extract full article body from HTML."""
    soup = BeautifulSoup(html, "lxml")
    
    # Try multiple selectors to find body content
    selectors = [
        "article .view-content",
        "div.se-main-container",
        "div.post-content",
        "div.article-content",
        "div.entry-content",
        "#postViewArea",
        ".view-content",
        "article",
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            # Remove script, style, and ad elements
            for tag in elem.select("script, style, .ads, .advertisement, .comments"):
                tag.decompose()
            
            text = elem.get_text(" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            
            if text and len(text) > 100:
                return text
    
    return ""


def fetch_html(session: requests.Session, url: str, timeout: int = 15) -> str:
    """Fetch HTML from URL with retries."""
    for attempt in range(3):
        try:
            res = session.get(url, timeout=timeout)
            if res.status_code == 200:
                return res.text
        except requests.RequestException as e:
            if attempt < 2:
                time.sleep(1)
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


def update_posts_with_full_content(posts_path: Path, output_path: Path) -> None:
    """
    Load existing posts and fetch full content from source URLs.
    """
    # Load existing data
    posts = json.loads(posts_path.read_text(encoding="utf-8"))
    session = build_session()
    
    print(f"[START] Fetching full content for {len(posts)} articles")
    print("=" * 60)
    
    updated_count = 0
    failed_count = 0
    skipped_count = 0
    
    for idx, item in enumerate(posts, start=1):
        source_url = item.get("source_url", "")
        title = item.get("title", "")
        
        if not source_url:
            skipped_count += 1
            print(f"[{idx}/{len(posts)}] SKIP (no source_url)")
            continue
        
        # Fetch full content
        html = fetch_html(session, source_url)
        if not html:
            failed_count += 1
            print(f"[{idx}/{len(posts)}] FAIL: {title[:40]}")
            continue
        
        # Extract full body
        body = extract_full_body(html)
        if not body:
            failed_count += 1
            print(f"[{idx}/{len(posts)}] FAIL (no body): {title[:40]}")
            continue
        
        # Update item with full content
        item["body"] = body
        
        # Recalculate category based on full content
        category = classify_category(title, body)
        item["category"] = category
        
        # Update summary with first 260 chars of body
        item["summary"] = body[:260] + ("..." if len(body) > 260 else "")
        
        # Update excerpt with first 1000 chars of body
        item["excerpt"] = body[:1000]
        
        # Update fetched_at
        item["fetched_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
        
        updated_count += 1
        body_preview = body[:50].replace("\n", " ") + "..."
        print(f"[{idx}/{len(posts)}] OK: {title[:40]} | {category}")
        
        # Rate limiting
        time.sleep(0.8 + random.random() * 0.3)
    
    print("=" * 60)
    print(f"[RESULT] Updated: {updated_count}, Failed: {failed_count}, Skipped: {skipped_count}")
    
    # Save updated posts
    output_path.write_text(
        json.dumps(posts, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[DONE] Saved to {output_path}")


def main() -> None:
    posts_path = Path("data/posts.json")
    output_path = Path("data/posts.json")
    
    if not posts_path.exists():
        print(f"[ERROR] {posts_path} not found")
        return
    
    update_posts_with_full_content(posts_path, output_path)


if __name__ == "__main__":
    main()
