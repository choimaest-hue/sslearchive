"""Test the improved scraper on previously truncated articles."""
import json
import sys
sys.path.insert(0, ".")

from scripts.scrape_all_pages import extract_full_body, build_session, fetch_html

session = build_session()

test_urls = [
    ("판레전드 : 본인이 잘못한걸 모르는 완전체 부부", "https://www.ssletv.com/entry/%ED%8C%90%EB%A0%88%EC%A0%84%EB%93%9C-%EB%B3%B8%EC%9D%B8%EC%9D%B4-%EC%9E%98%EB%AA%BB%ED%95%9C%EA%B1%B8-%EB%AA%A8%EB%A5%B4%EB%8A%94-%EC%99%84%EC%A0%84%EC%B2%B4-%EB%B6%80%EB%B6%80", 123),
    ("[판 고민 소름레전드] 친누나가 x떡이 되도록 때렸습니다", "https://www.ssletv.com/entry/%ED%8C%90-%EA%B3%A0%EB%AF%BC-%EC%86%8C%EB%A6%84%EB%A0%88%EC%A0%84%EB%93%9C-%EC%B9%9C%EB%88%84%EB%82%98%EA%B0%80-x%EB%96%A1%EC%9D%B4-%EB%90%98%EB%8F%84%EB%A1%9D-%EB%95%8C%EB%A0%B8%EC%8A%B5%EB%8B%88%EB%8B%A4feat-%EB%8C%93%EA%B8%80%EB%B9%8C%EB%9F%B0", 160),
    ("[판레전드]시댁에서 지원받은만큼 잘하라는 예비신랑", "https://www.ssletv.com/entry/%ED%8C%90%EB%A0%88%EC%A0%84%EB%93%9C%EC%8B%9C%EB%8C%81%EC%97%90%EC%84%9C-%EC%A7%80%EC%9B%90%EB%B0%9B%EC%9D%80%EB%A7%8C%ED%81%BC-%EC%9E%98%ED%95%98%EB%9D%BC%EB%8A%94-%EC%98%88%EB%B9%84%EC%8B%A0%EB%9E%91", 160),
    ("판레전드 - [짧음주의] 딸아이가 이름을 진매화로", "https://www.ssletv.com/entry/%ED%8C%90%EB%A0%88%EC%A0%84%EB%93%9C-%EC%A7%A7%EC%9D%8C%EC%A3%BC%EC%9D%98-%EB%94%B8%EC%95%84%EC%9D%B4%EA%B0%80-%EC%9D%B4%EB%A6%84%EC%9D%84-%EC%A7%84%EB%A7%A4%ED%99%94%EB%A1%9C-%EB%B0%94%EA%BE%B8%EA%B2%A0%EB%8B%A4%EB%8A%94%EB%8D%B0-%EB%82%A8%ED%8E%B8%EC%9D%B4-%EC%88%A0%EC%A7%91%EB%85%84%EA%B0%99%EB%8B%A4%EB%84%A4%EC%9A%94", 106),
    ("아프리카 꼬마 후원할 수 밖에 없게된 썰", "https://www.ssletv.com/entry/%EC%95%84%ED%94%84%EB%A6%AC%EC%B9%B4-%EA%BC%AC%EB%A7%88-%ED%9B%84%EC%9B%90%ED%95%A0-%EC%88%98-%EB%B0%96%EC%97%90-%EC%97%86%EA%B2%8C%EB%90%9C-%EC%8D%B0", 170),
]

for title, url, old_len in test_urls:
    html = fetch_html(session, url)
    body = extract_full_body(html)
    print(f"{'='*60}")
    print(f"TITLE: {title}")
    print(f"OLD: {old_len} chars -> NEW: {len(body)} chars  ({'IMPROVED' if len(body) > old_len else 'SAME/WORSE'})")
    print(f"FIRST 200: {body[:200]}")
    print(f"LAST 200: ...{body[-200:]}")
    print()
