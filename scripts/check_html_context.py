"""Check HTML context of images in sample pages"""
import json, requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin

with open("data/posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

# Sample: 1 normal 판 post, 1 multi-image 판 post, 1 LoL post, 1 군대 post
samples = []
for p in posts:
    imgs = len(p.get("comment_capture_urls", []))
    title = p["title"]
    if "롤 챔프" in title:
        samples.append(("LOL", p))
    elif "예비새언니" in title and imgs == 3:
        samples.append(("PAN_MULTI", p))
    elif "신랑 생각 없는" in title:
        samples.append(("PAN_SINGLE", p))
    elif "상황 터진 날 연대장" in title:
        samples.append(("ARMY", p))
    if len(samples) == 4:
        break

for label, p in samples:
    print(f"\n{'='*60}")
    print(f"[{label}] {p['title']} (imgs={len(p.get('comment_capture_urls',[]))})")
    print(f"{'='*60}")

    resp = session.get(p["source_url"], timeout=15)
    soup = BeautifulSoup(resp.text, "lxml")

    # Remove noise
    for sel in ["script", "style", "noscript", "iframe",
                "ins.adsbygoogle", "div.revenue_unit_wrap",
                "div.container_postbtn", "div[data-tistory-react-app]",
                ".another_category", ".related-post",
                "nav", "header", "footer", ".sidebar"]:
        for tag in soup.select(sel):
            tag.decompose()

    content = soup.select_one("div.tt_article_useless_p_margin")
    if not content:
        content = soup.select_one("div.entry-content")
    if not content:
        print("  NO CONTENT CONTAINER FOUND")
        continue

    # Find all images in content area
    for img in content.select("img"):
        src = img.get("data-src") or img.get("src") or ""
        if not src or src.startswith("data:"):
            continue
        full_url = urljoin(p["source_url"], src)
        if not full_url.startswith("http"):
            continue

        # Get parent context
        parent = img.parent
        parent_tag = parent.name if parent else "none"
        parent_class = parent.get("class", []) if parent else []

        # Get grandparent
        gp = parent.parent if parent else None
        gp_tag = gp.name if gp else "none"
        gp_class = gp.get("class", []) if gp else []

        # Get surrounding text (prev and next siblings)
        prev_text = ""
        next_text = ""
        if parent:
            prev_sib = parent.find_previous_sibling()
            if prev_sib:
                prev_text = prev_sib.get_text(strip=True)[:80]
            next_sib = parent.find_next_sibling()
            if next_sib:
                next_text = next_sib.get_text(strip=True)[:80]

        w = img.get("width", "?")
        h = img.get("height", "?")

        print(f"\n  IMG: ...{full_url[-40:]}")
        print(f"    size: {w}x{h}")
        print(f"    parent: <{parent_tag} class={parent_class}>")
        print(f"    grandparent: <{gp_tag} class={gp_class}>")
        print(f"    prev_text: {prev_text[:60]}")
        print(f"    next_text: {next_text[:60]}")

print("\nDone!")
