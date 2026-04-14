import json

with open("data/posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

# Show posts with many images
for p in posts:
    urls = p.get("comment_capture_urls", [])
    if len(urls) >= 3:
        print(f"=== [{len(urls)} imgs] {p['title']} ===")
        print(f"    source: {p['source_url']}")
        for i, u in enumerate(urls):
            print(f"  [{i}] {u}")
        print()

# Also show 2-image posts (first 5)
print("\n=== SAMPLE 2-IMAGE POSTS ===\n")
count = 0
for p in posts:
    urls = p.get("comment_capture_urls", [])
    if len(urls) == 2:
        print(f"=== [{len(urls)} imgs] {p['title']} ===")
        print(f"    source: {p['source_url']}")
        for i, u in enumerate(urls):
            print(f"  [{i}] {u}")
        print()
        count += 1
        if count >= 5:
            break

# Check blog.kakaocdn.net images
print("\n=== BLOG.KAKAOCDN.NET IMAGES ===\n")
for p in posts:
    urls = p.get("comment_capture_urls", [])
    for u in urls:
        if "blog.kakaocdn.net" in u:
            print(f"  {p['title']}")
            print(f"    source: {p['source_url']}")
            print(f"    img: {u}")
            print()
