"""Fetch articles from websites via RSS feed, HTML scraping, or Hugging Face releases."""

import re
import time
import feedparser
import requests
from bs4 import BeautifulSoup


HEADERS = {"User-Agent": "NewsAgent/1.0 (morning digest bot)"}

HF_MODELS_API = "https://huggingface.co/api/models"
# Quantized or repackaged builds of a model that was already released
HF_BUILD_VARIANTS = re.compile(
    r"fp8|fp4|int4|int8|gguf|awq|gptq|mlx|qat|w4a16|dspark|dflash|eagle3|-ct$|-hf$", re.I
)


def fetch_articles(site_config: dict) -> list[dict]:
    """Return a list of articles from a site as {title, url, content, date}."""
    if site_config.get("hf_author"):
        return _fetch_from_huggingface(site_config)
    if site_config.get("rss_url"):
        articles = _fetch_from_rss(site_config)
    else:
        articles = _fetch_from_html(site_config)
    return [
        a for a in articles
        if _passes_filters(a["title"] + " " + a["content"], a["title"] + " " + a["url"], site_config)
    ]


def _passes_filters(include_text: str, exclude_text: str, site_config: dict) -> bool:
    """Apply a site's include_keywords / exclude_keywords (case-insensitive regexes)."""
    include = site_config.get("include_keywords") or []
    exclude = site_config.get("exclude_keywords") or []
    if include and not any(re.search(p, include_text, re.I) for p in include):
        return False
    return not any(re.search(p, exclude_text, re.I) for p in exclude)


def _fetch_from_rss(site_config: dict) -> list[dict]:
    # Fetch with requests so a web-filter block shows up as an HTTP error, not a parse error
    response = requests.get(site_config["rss_url"], timeout=30, headers=HEADERS)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"unreadable feed: {feed.get('bozo_exception')}")
    articles = []
    for entry in feed.entries:
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        articles.append({
            "title": entry.get("title", "").strip(),
            "url": entry.get("link", ""),
            "content": BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True),
            # YYYY-MM-DD for the lookback check; feeds give RFC 822 or ISO timestamps
            "date": time.strftime("%Y-%m-%d", parsed) if parsed else "",
        })
    return articles


def _fetch_from_huggingface(site_config: dict) -> list[dict]:
    """Return one article per release day from a Hugging Face org's new model repos.

    A release usually ships several repos at once (sizes, base and instruct), so
    repos created on the same day are grouped. Quantized builds are skipped.
    """
    params = {"author": site_config["hf_author"], "sort": "createdAt", "direction": -1, "limit": 50}
    if site_config.get("hf_search"):
        params["search"] = site_config["hf_search"]
    response = requests.get(HF_MODELS_API, params=params, timeout=30, headers=HEADERS)
    response.raise_for_status()

    releases: dict[str, list[str]] = {}
    for model in response.json():
        name = model["id"].split("/", 1)[1]
        if HF_BUILD_VARIANTS.search(name) or not _passes_filters(name, name, site_config):
            continue
        releases.setdefault(model["createdAt"][:10], []).append(model["id"])

    articles = []
    for day, repos in releases.items():
        repos.sort(key=len)
        names = [r.split("/", 1)[1] for r in repos]
        urls = [f"https://huggingface.co/{r}" for r in repos]
        articles.append({
            "title": ", ".join(names[:3]) + (f" (+{len(names) - 3} more)" if len(names) > 3 else ""),
            "url": urls[0],
            "related_urls": urls,
            "content": "",
            "date": day,
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
    if url.startswith("https://huggingface.co/"):
        return _fetch_hf_model_card(url)
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


def _fetch_hf_model_card(url: str) -> dict:
    """Return a Hugging Face model card as plain text. The repo name stays the title."""
    try:
        response = requests.get(url + "/raw/main/README.md", timeout=30, headers=HEADERS)
        response.raise_for_status()
        text = re.sub(r"\A---\n.*?\n---\n", "", response.text, flags=re.S)  # YAML front matter
        text = BeautifulSoup(text, "html.parser").get_text()
        text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
        return {"title": "", "content": text[:5000]}
    except Exception as exc:
        return {"title": "", "content": f"Could not fetch content: {exc}"}
