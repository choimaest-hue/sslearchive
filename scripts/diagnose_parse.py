import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.scrape_all_pages import (
    BASE_CATEGORY_URL,
    build_session,
    extract_article_links_from_page,
    fetch_html,
    parse_article,
)


def main() -> None:
    session = build_session()
    links: list[str] = []

    for page in range(1, 151):
        url = BASE_CATEGORY_URL if page == 1 else f"{BASE_CATEGORY_URL}?page={page}"
        html = fetch_html(session, url)
        if not html:
            print(f"fetch-fail page={page}")
            break

        page_links = extract_article_links_from_page(html)
        if not page_links:
            print(f"no-links page={page}")
            break

        for link in page_links:
            if link not in links:
                links.append(link)

    print("unique_links", len(links))

    sample = links[350:550]
    ok = 0
    for url in sample:
        article_html = fetch_html(session, url)
        article = parse_article(article_html, url) if article_html else None
        if article:
            ok += 1

    print("sample_size", len(sample), "ok", ok, "fail", len(sample) - ok)


if __name__ == "__main__":
    main()
