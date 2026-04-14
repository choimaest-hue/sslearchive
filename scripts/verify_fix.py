import json

d = json.load(open('data/posts.json', 'r', encoding='utf-8'))

checks = {
    '완전체 부부': 123,
    '친누나가': 160,
    '예비신랑': 160,
    '아프리카 꼬마': 170,
}

for keyword, old_len in checks.items():
    for p in d:
        if keyword in p['title']:
            new_len = len(p['body'])
            ratio = new_len / old_len if old_len > 0 else 0
            print(f"{keyword}: {old_len} -> {new_len} chars ({ratio:.1f}x)")
            break
    else:
        print(f"{keyword}: NOT FOUND")
