import json

with open("data/posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

keywords = ["판", "레전드", "네이트", "사이다", "빡침", "역관광", "결시친", "억울",
            "고민", "훈훈", "이혼", "무개념", "소름", "반대", "어이", "찬반", "공감",
            "깜놀", "주작"]

non_pan = [p for p in posts
           if not any(kw in p["title"] for kw in keywords)
           and len(p.get("comment_capture_urls", [])) > 0]

print(f"Non-pan with imgs: {len(non_pan)}")
print(f"Total imgs: {sum(len(p.get('comment_capture_urls', [])) for p in non_pan)}")

cats = {}
for p in non_pan:
    c = p["category"]
    cats[c] = cats.get(c, 0) + 1
print(f"Categories: {cats}")

# Check how many have 롤 or game content
game_kw = ["롤", "챔프", "템트리", "스킬", "스토리"]
game_posts = [p for p in non_pan if any(kw in p["title"] for kw in game_kw)]
print(f"\nGame posts: {len(game_posts)}")
for p in game_posts:
    print(f"  {p['title']} (imgs={len(p.get('comment_capture_urls', []))})")

# Check: all non-pan with >1 image
multi = [p for p in non_pan if len(p.get("comment_capture_urls", [])) > 1]
print(f"\nNon-pan with >1 image: {len(multi)}")
for p in multi:
    print(f"  {p['title']} (imgs={len(p.get('comment_capture_urls', []))})")
