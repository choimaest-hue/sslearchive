import json
import random
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.scrape_all_pages import build_session, extract_capture_image_urls, fetch_html


def main() -> None:
    data_path = Path("data/posts.json")
    if not data_path.exists():
        print("[ERR] data/posts.json not found")
        return

    posts = json.loads(data_path.read_text(encoding="utf-8"))
    session = build_session()

    total = len(posts)
    updated = 0

    for idx, post in enumerate(posts, start=1):
        url = (post.get("source_url") or "").strip()
        if not url:
            post["comment_capture_urls"] = []
            continue

        html = fetch_html(session, url)
        if not html:
            post["comment_capture_urls"] = post.get("comment_capture_urls") or []
            continue

        captures = extract_capture_image_urls(html, url)
        post["comment_capture_urls"] = captures
        if captures:
            updated += 1

        if idx <= 20 or idx % 50 == 0 or idx == total:
            print(f"[{idx}/{total}] captures={len(captures)}")

        time.sleep(0.35 + random.random() * 0.25)

    data_path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] updated posts with captures: {updated}/{total}")


if __name__ == "__main__":
    main()
