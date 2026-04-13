# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

A Python CLI agent that checks a configurable list of websites each morning for new publications, uses Claude to summarize each article, and writes the summaries to a Notion database ("News Agent Digest" under the "Top Of Mind" page in Sean's workspace).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent (fetches and summarizes new articles, writes to Notion)
python cli.py run
python cli.py run --verbose   # show per-article progress

# Manage monitored sites
python cli.py sites list
python cli.py sites add "OpenAI" "https://openai.com/news" --rss "https://openai.com/news/rss"
python cli.py sites add "Google DeepMind" "https://deepmind.google/discover/blog/"
python cli.py sites remove "OpenAI"
```

## Environment variables (copy `.env.example` → `.env`)

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `NOTION_API_KEY` | Notion integration token |
| `NOTION_DATABASE_ID` | Pre-set to the created database (`d423fe7ae84745c4b2538a2311ab56f6`) |
| `SLACK_WEBHOOK_URL` | Optional — if set, posts a digest summary to Slack after each run |

## Architecture

```
cli.py          → Click CLI entry point (run / sites add|remove|list)
agent.py        → Orchestration loop: fetch → summarize → write → notify
scraper.py      → Fetch article lists (RSS via feedparser, or HTML via BeautifulSoup)
                  + fetch_article_content() for full article text
summarizer.py   → Claude API call; returns {summary, category}
notion_writer.py→ notion-client SDK; creates one Notion page per article
notifier.py     → Posts Slack digest via webhook (skipped silently if no webhook configured)
state.py        → Tracks seen URLs in state.json to prevent duplicate processing
config.yaml     → List of monitored sites + settings (lookback_days, max_articles_per_run)
```

**Data flow:** `cli.py run` → `agent.run()` iterates sites in `config.yaml` → `scraper.fetch_articles()` returns article links → unseen URLs are fetched for full content → `summarizer.summarize_article()` calls Claude → `notion_writer.write_article()` creates a Notion page → `state.mark_seen()` records the URL → `notifier.notify_slack()` posts digest.

## Notion database schema

Database ID: `d423fe7ae84745c4b2538a2311ab56f6`  
Location: Notion → Sean's Personal → Top Of Mind → News Agent Digest

| Property | Type | Notes |
|---|---|---|
| Title | title | Article headline |
| Date | date | Publication date (defaults to today) |
| Site | select | Source site name (new values auto-created) |
| Category | select | Blog Post / Research Paper / Product Update / News / Other |
| Summary | rich_text | Claude's 2-3 sentence summary |
| URL | url | Link to original article |
| Read | checkbox | Manual tracking |

## Adding a new site

Sites without RSS feeds use HTML scraping. The `scrape.articles_selector` CSS selector determines which `<a>` tags are treated as article links. For sites where the default `"a"` selector is too broad, refine it (e.g. `"a[href*='/blog/']"`). Use `scrape.exclude_url_patterns` (list of substrings) to filter out non-article links like team/about pages.

Use `notion_label` in a site entry to override the Notion "Site" select value (e.g. two Anthropic feeds both label as `"Anthropic"`).

When a site name not in the existing Notion select options is written, the Notion API auto-creates a new option — no manual Notion config needed.

## Scheduling (daily automation)

To run automatically each morning, add a cron job:
```bash
# Run at 7am every day
0 7 * * * cd /path/to/News_Agent && /path/to/python cli.py run >> ~/news_agent.log 2>&1
```
