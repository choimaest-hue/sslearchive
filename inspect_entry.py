import requests
from bs4 import BeautifulSoup

# 첫 번째 기사 URL 테스트
url = "https://www.ssletv.com/entry/%ED%8C%90-%EC%86%8C%EB%A6%84-%EB%A0%88%EC%A0%84%EB%93%9C-%EC%95%8C%EC%BD%9C%EC%A4%91%EB%8B%85%EC%9E%90-%EC%97%AC%EC%B9%9C%EC%9D%B4-%EA%B2%B0%ED%98%BC%ED%95%98%EC%9E%90%EA%B3%A0-%ED%95%A9%EB%8B%88%EB%8B%A4"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

try:
    res = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {res.status_code}")
    print(f"URL: {url}")
    print("-" * 80)
    
    # Save HTML for inspection
    with open('entry_page.html', 'w', encoding='utf-8') as f:
        f.write(res.text)
    
    soup = BeautifulSoup(res.text, 'lxml')
    
    # Find all potential content containers
    print("\n[구조 분석]")
    
    # Check for common content selectors
    selectors = [
        ("article", "article"),
        ("div.se-main-container", "div.se-main-container"),
        ("div.post-content", "div.post-content"),
        ("div#content", "div#content"),
        ("div.entry-content", "div.entry-content"),
        ("div.view-content", "div.view-content"),
        ("div.tt_article_useless_p_margin.tt_article_border_left_blue.TComment2_Container", "div.tt_article_useless_p_margin..."),
    ]
    
    for name, selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text()[:100]
            print(f"✓ Found: {name}")
            print(f"  Preview: {text}")
    
    # Check for divs with role or data attributes
    main_content = soup.find('div', {'role': 'main'})
    if main_content:
        print("✓ Found div[role=main]")
    
    # List all major divs
    print("\n[주요 div 클래스 목록]")
    for div in soup.find_all('div', class_=True, limit=20):
        classes = ' '.join(div.get('class', []))
        if len(classes) < 50:
            print(f"  .{classes}")
    
    print("\n✓ Full HTML saved to entry_page.html")
    
except Exception as e:
    print(f"Error: {e}")
