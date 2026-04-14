"""
Filter comment_capture_urls:
- Keep images for community story posts (판, 썰 etc.) = actual comment captures
- Remove images for non-community content posts (game guides, marketing articles etc.)
- blog.kakaocdn.net images: keep (they're valid Kakao CDN Tistory uploads)

Analysis results:
- 947 posts with 1 image: all genuine comment captures
- 49 posts with 2 images: almost all multi-part captures
- 6 posts with 3+ images: multi-part captures (except LoL post)
- LoL post: 7 game images = NOT captures -> clear
- 바이럴마케팅: 2 images = NOT captures -> clear
- Total contamination: ~9 images across 2 posts
"""
import json, re

with open("data/posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

# Track changes
changes = []
before_total = sum(len(p.get("comment_capture_urls", [])) for p in posts)

# Non-community content patterns (posts that are NOT story/comment captures)
non_community_patterns = [
    r"롤\s*챔프",
    r"바이럴마케팅",
    r"템트리.*능력치.*스킬",
]

for p in posts:
    title = p["title"]
    imgs = p.get("comment_capture_urls", [])
    if not imgs:
        continue

    is_non_community = any(re.search(pat, title) for pat in non_community_patterns)

    if is_non_community:
        changes.append({
            "title": title,
            "action": "CLEAR",
            "removed": len(imgs),
            "urls": imgs[:3],
        })
        p["comment_capture_urls"] = []

after_total = sum(len(p.get("comment_capture_urls", [])) for p in posts)

print(f"Before: {before_total} total images")
print(f"After:  {after_total} total images")
print(f"Removed: {before_total - after_total} images from {len(changes)} posts")

for c in changes:
    print(f"\n  [{c['action']}] {c['title']} (-{c['removed']} imgs)")
    for u in c["urls"]:
        print(f"    {u}")

# Distribution after
from collections import Counter
dist = Counter(len(p.get("comment_capture_urls", [])) for p in posts)
print(f"\nImage count distribution after filtering:")
for k in sorted(dist.keys()):
    print(f"  {k} images: {dist[k]} posts")

# Save
with open("data/posts.json", "w", encoding="utf-8") as f:
    json.dump(posts, f, ensure_ascii=False, indent=2)

print(f"\nSaved updated data/posts.json")
