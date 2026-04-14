"""Deep dive into center tag structure"""
import requests
from bs4 import BeautifulSoup

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

# Check: "본인이 잘못한걸 모르는 완전체 부부" - 123 chars vs 508 raw
url = "https://www.ssletv.com/entry/%ED%8C%90%EB%A0%88%EC%A0%84%EB%93%9C-%EB%B3%B8%EC%9D%B8%EC%9D%B4-%EC%9E%98%EB%AA%BB%ED%95%9C%EA%B1%B8-%EB%AA%A8%EB%A5%B4%EB%8A%94-%EC%99%84%EC%A0%84%EC%B2%B4-%EB%B6%80%EB%B6%80"

resp = session.get(url, timeout=15)
soup = BeautifulSoup(resp.text, "lxml")
container = soup.select_one("div.tt_article_useless_p_margin")

print("=== FULL RAW HTML of container (first 3000 chars) ===")
html_str = str(container)[:3000]
print(html_str)
print(f"\n\nTotal HTML length: {len(str(container))}")

# Check second article
print("\n\n" + "="*70)
url2 = "https://www.ssletv.com/entry/%ED%8C%90-%EA%B3%A0%EB%AF%BC-%EC%86%8C%EB%A6%84%EB%A0%88%EC%A0%84%EB%93%9C-%EC%B9%9C%EB%88%84%EB%82%98%EA%B0%80-x%EB%96%A1%EC%9D%B4-%EB%90%98%EB%8F%84%EB%A1%9D-%EB%95%8C%EB%A0%B8%EC%8A%B5%EB%8B%88%EB%8B%A4feat-%EB%8C%93%EA%B8%80%EB%B9%8C%EB%9F%B0"
resp2 = session.get(url2, timeout=15)
soup2 = BeautifulSoup(resp2.text, "lxml")
container2 = soup2.select_one("div.tt_article_useless_p_margin")
print("=== HTML structure of '친누나' post (first 3000) ===")
html_str2 = str(container2)[:3000]
print(html_str2)

# Also check 4th: 시댁에서 지원받은만큼
print("\n\n" + "="*70)
url3 = "https://www.ssletv.com/entry/%ED%8C%90%EB%A0%88%EC%A0%84%EB%93%9C%EC%8B%9C%EB%8C%81%EC%97%90%EC%84%9C-%EC%A7%80%EC%9B%90%EB%B0%9B%EC%9D%80%EB%A7%8C%ED%81%BC-%EC%9E%98%ED%95%98%EB%9D%BC%EB%8A%94-%EC%98%88%EB%B9%84%EC%8B%A0%EB%9E%91"
resp3 = session.get(url3, timeout=15)
soup3 = BeautifulSoup(resp3.text, "lxml")
container3 = soup3.select_one("div.tt_article_useless_p_margin")
print("=== HTML structure of '예비신랑' post (first 3000) ===")
html_str3 = str(container3)[:3000]
print(html_str3)
