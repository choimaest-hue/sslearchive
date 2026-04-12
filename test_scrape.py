import requests
from bs4 import BeautifulSoup

r = requests.get('https://www.ssletv.com/category/%EC%8D%B0%20%EC%A0%84%EC%9A%A9%20%EB%AA%A8%EC%9D%8C%EC%86%8C')
soup = BeautifulSoup(r.text, 'lxml')

# Save HTML for inspection
with open('category_page.html', 'w', encoding='utf-8') as f:
    f.write(r.text)

# Try different selectors
for selector in ['a[href]', 'article', '.post', '.entry', 'div.card', 'li']:
    items = soup.select(selector)
    if items:
        print(f"Found {len(items)} items with selector: {selector}")
        if selector == 'a[href]':
            for item in items[:5]:
                href = item.get('href', '')
                if href and 'entry' in href:
                    print(f"  -> {href}")
