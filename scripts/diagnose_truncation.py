"""Diagnose truncated articles by comparing scraped body with actual page content."""
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

with open("data/posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

# Sort by body length, check shortest ones
posts_by_len = sorted(posts, key=lambda p: len(p["body"]))

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

# Check first 5 shortest articles
for p in posts_by_len[:5]:
    print(f"\n{'='*70}")
    print(f"TITLE: {p['title']}")
    print(f"BODY LEN: {len(p['body'])} chars")
    print(f"URL: {p['source_url']}")
    print(f"CURRENT BODY (first 200): {p['body'][:200]}...")
    print(f"CURRENT BODY (last 200): ...{p['body'][-200:]}")
    
    # Fetch actual page
    resp = session.get(p["source_url"], timeout=15)
    soup = BeautifulSoup(resp.text, "lxml")
    
    # Get raw content container
    container = soup.select_one("div.tt_article_useless_p_margin")
    if not container:
        container = soup.select_one("div.entry-content")
    if not container:
        print("  NO CONTAINER!")
        continue
    
    # Get full raw text (no filtering)
    raw_text = container.get_text("\n", strip=True)
    print(f"RAW PAGE TEXT LEN: {len(raw_text)} chars")
    print(f"RAW TEXT (first 300): {raw_text[:300]}...")
    print(f"RAW TEXT (last 300): ...{raw_text[-300:]}")
    
    # Show all child elements structure
    print(f"\nCHILD ELEMENTS:")
    for i, child in enumerate(container.children):
        if hasattr(child, 'name') and child.name:
            classes = child.get("class", [])
            text_preview = child.get_text(strip=True)[:80]
            # Check if it looks like an ad
            is_ad = False
            if child.select("ins.adsbygoogle, [class*='adfit'], a[href*='ader.naver']"):
                is_ad = True
            if child.get("data-tistory-react-app") is not None:
                is_ad = True
            print(f"  [{i:3d}] <{child.name} class={classes}> {'[AD]' if is_ad else ''} text={text_preview[:60]}")
    
    print()
