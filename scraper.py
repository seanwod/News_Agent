"""Fetch articles from websites via RSS feed or HTML scraping."""

import re
import feedparser
import requests
from bs4 import BeautifulSoup


HEADERS = {"User-Agent": "NewsAgent/1.0 (morning digest bot)"}


def fetch_articles(site_config: dict) -> list[dict]:
    """Return a list of articles from a site as {title, url, content, date}."""
    if site_config.get("rss_url"):
        return _fetch_from_rss(site_config)
    return _fetch_from_html(site_config)


def _fetch_from_rss(site_config: dict) -> list[dict]:
    feed = feedparser.parse(site_config["rss_url"])
    articles = []
    for entry in feed.entries:
        articles.append({
            "title": entry.get("title", "").strip(),
            "url": entry.get("link", ""),
            "content": entry.get("summary", ""),
            "date": entry.get("published", ""),
        })
    return articles


def _fetch_from_html(site_config: dict) -> list[dict]:
    scrape_cfg = site_config.get("scrape", {})
    selector = scrape_cfg.get("articles_selector", "a")
    base_url = scrape_cfg.get("base_url", "")

    response = requests.get(site_config["url"], timeout=30, headers=HEADERS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    exclude_patterns = [re.compile(p) for p in scrape_cfg.get("exclude_url_patterns", [])]

    seen_urls: set[str] = set()
    articles = []
    for link in soup.select(selector):
        href = link.get("href", "").strip()
        if not href:
            continue
        if not href.startswith("http"):
            href = base_url + href
        if href in seen_urls:
            continue
        seen_urls.add(href)

        # Skip the index page itself
        if href.rstrip("/").endswith(("/news", "/research")):
            continue

        # Skip URLs matching exclude patterns
        if any(p.search(href) for p in exclude_patterns):
            continue

        title = link.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        articles.append({"title": title, "url": href, "content": "", "date": ""})

    return articles


def fetch_article_content(url: str) -> dict:
    """Fetch an article URL and return {title, content}.

    The title comes from the page's <h1> (more reliable than link text).
    Content is the main readable text, capped at 5000 chars.
    """
    try:
        response = requests.get(url, timeout=30, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract clean title from <h1>
        h1 = soup.find("h1")
        clean_title = h1.get_text(strip=True) if h1 else ""

        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(class_=re.compile(r"content|post|article|body", re.I))
        )
        text = (main or soup).get_text(separator="\n", strip=True)
        return {"title": clean_title, "content": text[:5000]}
    except Exception as exc:
        return {"title": "", "content": f"Could not fetch content: {exc}"}
