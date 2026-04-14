import json

with open("data/posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

has_comments = [p for p in posts if p.get("comments") and len(p["comments"]) > 0]
print(f"Posts with comments: {len(has_comments)}")
print(f"Total comments: {sum(len(p['comments']) for p in has_comments)}")

# Sample
if has_comments:
    p = has_comments[0]
    print(f"\nSample: {p['title']}")
    print(f"  comment_count: {p['comment_count']}")
    print(f"  comments[0]: {json.dumps(p['comments'][0], ensure_ascii=False)[:200]}")
