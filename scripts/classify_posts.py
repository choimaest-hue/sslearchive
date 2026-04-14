import json

with open("data/posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

# Find posts that don't look like natepan comment posts
keywords = ["판", "레전드", "네이트", "사이다", "빡침", "역관광", "결시친", "억울", "고민", "훈훈", "이혼", "무개념", "소름", "반대", "어이", "찬반", "공감", "깜놀", "주작"]

non_pan = []
for p in posts:
    title = p["title"]
    has_keyword = any(kw in title for kw in keywords)
    imgs = len(p.get("comment_capture_urls", []))
    if not has_keyword and imgs > 0:
        non_pan.append(p)
        print(f"[{p['category']}] {title} (imgs={imgs})")

print(f"\nTotal non-판 posts with images: {len(non_pan)}")
print(f"Total images in non-판 posts: {sum(len(p.get('comment_capture_urls',[])) for p in non_pan)}")

# Also check: pan posts without images
pan_no_img = [p for p in posts if any(kw in p["title"] for kw in keywords) and len(p.get("comment_capture_urls", [])) == 0]
print(f"\n판 posts without images: {len(pan_no_img)}")
for p in pan_no_img[:10]:
    print(f"  [{p['category']}] {p['title']}")
