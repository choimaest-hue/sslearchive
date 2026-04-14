import json
from collections import Counter
from urllib.parse import urlparse

with open("data/posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

# Show ALL image URLs for first 5 posts that have captures
count = 0
for p in posts:
    urls = p.get("comment_capture_urls", [])
    if urls and count < 5:
        count += 1
        print(f"=== [{count}] {p['title'][:50]} ({len(urls)} imgs) ===")
        print(f"    URL: {p.get('url','')}")
        for i, u in enumerate(urls):
            print(f"  [{i}] {u}")
        print()

# Count posts by image count
img_count_dist = Counter()
for p in posts:
    n = len(p.get("comment_capture_urls", []))
    img_count_dist[n] += 1
print("=== Image count distribution ===")
for n in sorted(img_count_dist.keys()):
    print(f"  {n} images: {img_count_dist[n]} posts")

# Show all unique image URL path patterns
print("\n=== Sample full URLs (first 20 unique) ===")
seen = set()
for p in posts:
    for u in p.get("comment_capture_urls", []):
        if u not in seen and len(seen) < 20:
            seen.add(u)
            print(f"  {u}")
