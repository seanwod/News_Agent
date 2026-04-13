"""Core agent logic: fetch → summarize → write to Notion."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from notion_writer import write_article
from notifier import notify_slack
from scraper import fetch_article_content, fetch_articles
from state import load_seen_urls, mark_seen
from summarizer import summarize_article

load_dotenv(Path(__file__).parent / ".env", override=True)

CONFIG_FILE = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def run(verbose: bool = False) -> list[dict]:
    """
    Main agent loop. For each configured site:
      1. Fetch article links
      2. Skip already-seen URLs
      3. Fetch full content, summarize with Claude
      4. Write to Notion

    Returns the list of newly processed articles.
    """
    config = load_config()
    settings = config.get("settings", {})
    max_articles = settings.get("max_articles_per_run", 10)

    seen_urls = load_seen_urls()
    new_urls: list[str] = []
    results: list[dict] = []

    for site in config.get("sites", []):
        site_name = site["name"]
        if verbose:
            print(f"\n[{site_name}] Checking {site['url']} ...")

        try:
            articles = fetch_articles(site)
        except Exception as exc:
            print(f"[{site_name}] ERROR fetching articles: {exc}")
            continue

        new_articles = [a for a in articles if a["url"] not in seen_urls][:max_articles]

        if verbose:
            print(f"[{site_name}] {len(new_articles)} new article(s) found.")

        for article in new_articles:
            if verbose:
                print(f"  Processing: {article['title'][:70]}...")

            if not article.get("content"):
                fetched = fetch_article_content(article["url"])
                article["content"] = fetched["content"]
                if fetched["title"]:
                    article["title"] = fetched["title"]

            summary_result = summarize_article(article["title"], article["content"], site_name)
            article["summary"] = summary_result["summary"]
            article["category"] = summary_result["category"]
            article["site"] = site.get("notion_label", site_name)

            try:
                notion_url = write_article(article)
                article["notion_url"] = notion_url
                new_urls.append(article["url"])
                results.append(article)
                if verbose:
                    print(f"  -> Notion: {notion_url}")
            except Exception as exc:
                print(f"  ERROR writing to Notion: {exc}")

    mark_seen(new_urls)
    notify_slack(results)
    return results
