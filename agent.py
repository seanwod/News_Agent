"""Core agent logic: fetch → summarize → post to Slack."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml
from dotenv import load_dotenv

from notifier import notify_slack
from scraper import fetch_article_content, fetch_articles
from state import load_last_scheduled_run, load_seen_urls, mark_seen
from summarizer import summarize_article

load_dotenv(Path(__file__).parent / ".env", override=True)

CONFIG_FILE = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def scheduled_run_due(now: datetime) -> bool:
    """True if a run_hours slot (Mac local time) has passed since the last scheduled run.

    launchd wakes the agent hourly and this decides. launchd keeps the time zone it
    booted with, so scheduling 6 AM in launchd itself drifts when the Mac travels.
    """
    hours = load_config().get("settings", {}).get("run_hours", [6, 14])
    slots = [
        now.replace(hour=h, minute=0, second=0, microsecond=0) - timedelta(days=d)
        for h in hours
        for d in (0, 1)
    ]
    latest_slot = max(s for s in slots if s <= now)
    last = load_last_scheduled_run()
    return last is None or last < latest_slot


def run(verbose: bool = False) -> list[dict]:
    """
    Main agent loop. For each configured site:
      1. Fetch article links
      2. Skip already-seen URLs
      3. Fetch full content, summarize with Claude
      4. Post the digest to Slack

    Returns the list of newly processed articles.
    """
    if not os.environ.get("SLACK_WEBHOOK_URL", "").strip():
        raise SystemExit("SLACK_WEBHOOK_URL is not set, so there is nowhere to post the digest.")

    config = load_config()
    settings = config.get("settings", {})
    max_articles = settings.get("max_articles_per_run", 10)
    cutoff = (date.today() - timedelta(days=settings.get("lookback_days", 7))).isoformat()

    seen_urls = load_seen_urls()
    new_urls: list[str] = []
    results: list[dict] = []

    fetch_failures = 0
    for site in config.get("sites", []):
        site_name = site["name"]
        if verbose:
            print(f"\n[{site_name}] Checking {site['url']} ...")

        try:
            articles = fetch_articles(site)
        except Exception as exc:
            print(f"[{site_name}] ERROR fetching articles: {exc}")
            fetch_failures += 1
            continue

        # Undated articles (HTML scrapes) rely on seen_urls alone
        new_articles = [
            a for a in articles
            if not seen_urls.intersection(a.get("related_urls") or [a["url"]])
            and (not a.get("date") or a["date"] >= cutoff)
        ][:max_articles]

        if verbose:
            print(f"[{site_name}] {len(new_articles)} new article(s) found.")

        for article in new_articles:
            if verbose:
                print(f"  Processing: {article['title'][:70]}...")

            # RSS summaries are often a single line, so fetch the full article too
            if len(article.get("content", "")) < 500:
                fetched = fetch_article_content(article["url"])
                if not article.get("content") or not fetched["content"].startswith("Could not fetch"):
                    article["content"] = fetched["content"]
                # HTML link text is messy; RSS and Hugging Face titles are already clean
                if fetched["title"] and not site.get("rss_url"):
                    article["title"] = fetched["title"]

            summary_result = summarize_article(article["title"], article["content"], site_name)
            article["summary"] = summary_result["summary"]
            article["category"] = summary_result["category"]
            article["site"] = site.get("label", site_name)
            new_urls.extend(article.get("related_urls") or [article["url"]])
            results.append(article)

    if fetch_failures == len(config.get("sites", [])):
        raise RuntimeError("every source failed to fetch (network not up yet?)")
    # Mark seen only once Slack has the digest, so a failed post retries next run
    if not notify_slack(results):
        raise RuntimeError("Slack post failed; these articles will be retried next run")
    mark_seen(new_urls)
    return results
