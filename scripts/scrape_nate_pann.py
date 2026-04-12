import argparse
import hashlib
import json
import random
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://pann.nate.com"
DEFAULT_SEEDS = [
    "https://pann.nate.com/talk/ranking/d",
    "https://pann.nate.com/talk/ranking/w",
    "https://pann.nate.com/talk/ranking/m",
]
CATEGORIES = ["10대 이야기", "20대 이야기", "30대 이야기", "결혼/시집/친정"]

TITLE_SELECTORS = ["h2", "h3", ".subject", ".post-title", "#subject"]
BODY_SELECTORS = ["#contentArea", ".post-content", ".view-content", ".content"]
COMMENT_SELECTORS = [
    ".comment-list li",
    ".cmt_list li",
    ".reply_list li",
    ".comment-item",
]


@dataclass
class ScrapeConfig:
    target_count: int
    max_ranking_pages: int
    top_per_page: int
    sleep_seconds: float
    timeout_seconds: int
    output_path: Path


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def sentence_summary(text: str, max_sentences: int = 3) -> str:
    parts = re.split(r"(?<=[.!?다])\s+", clean_text(text))
    return " ".join(parts[:max_sentences]).strip()


def category_from_text(title: str, body: str) -> str:
    t = f"{title} {body}"
    if re.search(r"10대|중학생|고등학생|학폭|급식", t):
        return "10대 이야기"
    if re.search(r"20대|취준|대학생|자취|인턴|첫직장", t):
        return "20대 이야기"
    if re.search(r"30대|육아|이직|대출|경력", t):
        return "30대 이야기"
    if re.search(r"결혼|시댁|친정|남편|아내|시어머니|장모", t):
        return "결혼/시집/친정"
    return "20대 이야기"


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }
    )
    return session


def fetch_html(session: requests.Session, url: str, timeout: int) -> str:
    for _ in range(3):
        try:
            res = session.get(url, timeout=timeout)
            if res.status_code == 200:
                return res.text
        except requests.RequestException:
            time.sleep(1)
    return ""


def parse_links_from_ranking(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        text = clean_text(a.get_text(" "))
        if not href:
            continue

        abs_url = urljoin(BASE_URL, href)
        parsed = urlparse(abs_url)
        if "pann.nate.com" not in parsed.netloc:
            continue

        path_ok = parsed.path.startswith("/talk/") or parsed.path.startswith("/talk/")
        query = parse_qs(parsed.query)
        has_post_id = "pann_id" in query or re.search(r"/\d{6,}", parsed.path)
        if path_ok and has_post_id:
            links.append(abs_url)
            continue

        if any(k in text for k in ["베스트", "랭킹", "월간", "주간", "일간"]):
            links.append(abs_url)

    deduped: list[str] = []
    seen = set()
    for url in links:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def pick_text(soup: BeautifulSoup, selectors: Iterable[str]) -> str:
    for sel in selectors:
        node = soup.select_one(sel)
        if node:
            text = clean_text(node.get_text(" "))
            if text:
                return text
    return ""


def collect_comments(soup: BeautifulSoup, limit: int = 12) -> list[str]:
    comments: list[str] = []
    for sel in COMMENT_SELECTORS:
        for node in soup.select(sel):
            text = clean_text(node.get_text(" "))
            if text and len(text) > 3:
                comments.append(text)
            if len(comments) >= limit:
                return comments[:limit]
    return comments[:limit]


def post_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "pann_id" in query and query["pann_id"]:
        return query["pann_id"][0]
    m = re.search(r"(\d{6,})", parsed.path)
    if m:
        return m.group(1)
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:12]


def parse_post(html: str, source_url: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")
    title = pick_text(soup, TITLE_SELECTORS)
    body = pick_text(soup, BODY_SELECTORS)

    if not title or not body:
        return None

    body_excerpt = clean_text(body)[:800]
    comments = [c[:200] for c in collect_comments(soup)]
    category = category_from_text(title, body_excerpt)

    date_text = ""
    for sel in [".date", ".write-date", ".post-date", "time"]:
        node = soup.select_one(sel)
        if node:
            date_text = clean_text(node.get_text(" "))
            break

    published_at = ""
    m = re.search(r"(20\d{2}[./-]\d{1,2}[./-]\d{1,2})", date_text)
    if m:
        published_at = m.group(1).replace(".", "-").replace("/", "-")

    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    return {
        "id": post_id_from_url(source_url),
        "title": title[:120],
        "source_url": source_url,
        "source_site": "nate pann",
        "published_at": published_at,
        "category": category,
        "summary": sentence_summary(body_excerpt, 3)[:260],
        "excerpt": body_excerpt,
        "comments": comments,
        "comment_count": len(comments),
        "fetched_at": now,
    }


def scrape(config: ScrapeConfig) -> list[dict]:
    session = build_session()

    ranking_pages: list[str] = []
    for seed in DEFAULT_SEEDS:
        for page in range(1, config.max_ranking_pages + 1):
            if "?" in seed:
                url = f"{seed}&page={page}"
            else:
                url = f"{seed}?page={page}"
            ranking_pages.append(url)

    post_candidates: list[str] = []
    seen_candidates = set()
    for idx, ranking_url in enumerate(ranking_pages, start=1):
        html = fetch_html(session, ranking_url, config.timeout_seconds)
        if not html:
            continue

        links = parse_links_from_ranking(html)
        post_links = [u for u in links if "pann_id" in u or re.search(r"/\d{6,}", urlparse(u).path)]

        for link in post_links[: config.top_per_page]:
            if link not in seen_candidates:
                seen_candidates.add(link)
                post_candidates.append(link)

        if idx % 10 == 0:
            print(f"[ranking] scanned {idx} pages, candidates={len(post_candidates)}")

        if len(post_candidates) >= config.target_count * 2:
            break

        time.sleep(config.sleep_seconds + random.random() * 0.5)

    collected: list[dict] = []
    seen_ids = set()
    for idx, post_url in enumerate(post_candidates, start=1):
        html = fetch_html(session, post_url, config.timeout_seconds)
        if not html:
            continue

        item = parse_post(html, post_url)
        if not item:
            continue

        if item["id"] in seen_ids:
            continue

        seen_ids.add(item["id"])
        collected.append(item)

        if idx % 25 == 0:
            print(f"[post] scanned {idx}, collected={len(collected)}")

        if len(collected) >= config.target_count:
            break

        time.sleep(config.sleep_seconds + random.random() * 0.6)

    return collected[: config.target_count]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Nate Pann 랭킹 페이지를 순회해 게시글 요약/댓글 요약 데이터를 수집합니다. "
            "저작권 이슈를 줄이기 위해 원문 전체가 아닌 요약과 발췌문 중심으로 저장합니다."
        )
    )
    parser.add_argument("--target-count", type=int, default=600)
    parser.add_argument("--max-ranking-pages", type=int, default=220)
    parser.add_argument("--top-per-page", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=1.1)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--output", type=str, default="data/posts.json")
    args = parser.parse_args()

    config = ScrapeConfig(
        target_count=max(1, args.target_count),
        max_ranking_pages=max(1, args.max_ranking_pages),
        top_per_page=max(1, args.top_per_page),
        sleep_seconds=max(0.2, args.sleep),
        timeout_seconds=max(5, args.timeout),
        output_path=Path(args.output),
    )

    print("[start] scraping...")
    items = scrape(config)
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    config.output_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] wrote {len(items)} items -> {config.output_path}")


if __name__ == "__main__":
    main()
