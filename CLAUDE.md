# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

A Python CLI agent that checks a configurable list of websites each morning for new publications, uses Claude to summarize each article, and posts a digest to Slack via an incoming webhook, grouped by company. (Until Sep 30, 2026 it also wrote each article to a Notion database, "News Agent Digest" under Top Of Mind. That database is still in Notion but no longer updated.)

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent (fetches and summarizes new articles, posts to Slack)
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
| `SLACK_WEBHOOK_URL` | Required. Incoming webhook the digest posts to. The run exits early if it is missing. |

## Architecture

```
cli.py          → Click CLI entry point (run / sites add|remove|list)
agent.py        → Orchestration loop: fetch → summarize → post
scraper.py      → Fetch article lists (RSS via feedparser, HTML via BeautifulSoup,
                  or Hugging Face model releases via the HF API)
                  + fetch_article_content() for full article text
summarizer.py   → Claude API call; returns {summary, category}
notifier.py     → Posts the Slack digest via webhook, grouped by site label, split if long
state.py        → Tracks seen URLs in state.json to prevent duplicate processing
config.yaml     → List of monitored sites + settings (lookback_days, max_articles_per_run)
```

**Data flow:** `cli.py run` → `agent.run()` iterates sites in `config.yaml` → `scraper.fetch_articles()` returns article links → unseen URLs are fetched for full content → `summarizer.summarize_article()` calls Claude → `notifier.notify_slack()` posts the digest → `state.mark_seen()` records the URLs only if the post succeeded, so a failed post is retried on the next run.

Each article gets a Category from Claude (Blog Post / Research Paper / Product Update / Model Release / News / Other), shown in brackets after the link.

## Adding a new site

Sites without RSS feeds use HTML scraping. The `scrape.articles_selector` CSS selector determines which `<a>` tags are treated as article links. For sites where the default `"a"` selector is too broad, refine it (e.g. `"a[href*='/blog/']"`). Use `scrape.exclude_url_patterns` (list of substrings) to filter out non-article links like team/about pages.

Use `label` in a site entry to set the heading it is grouped under in Slack (e.g. three Gemma sources all label as `"Gemma (Google)"`).

`include_keywords` and `exclude_keywords` (lists of case-insensitive regexes) work on any source. Include matches the title plus RSS summary; exclude matches the title plus URL. Use them to narrow a broad feed to one topic (the Google blogs filtered to Gemma). The Decoder, SCMP Tech, and Recode China AI share one keyword list through the YAML anchor `&open_weight_labs`. Note that `sites add` and `sites remove` rewrite `config.yaml` with `yaml.dump`, which drops comments and expands anchors.

**Hugging Face sources.** Open-weight labs (Kimi, Qwen, DeepSeek, GLM, MiMo, Nemotron, Gemma) are tracked through their Hugging Face orgs, because the corporate Zscaler filter blocks the labs' own sites on the work Mac. Set `hf_author` (and optionally `hf_search` for a server-side name filter) instead of `rss_url`. Repos created on the same day are grouped into one article, quantized builds (FP8, GGUF, QAT, etc.) are skipped via `HF_BUILD_VARIANTS` in `scraper.py`, and the summary is written from the model card. The `sites add` CLI does not support HF entries; edit `config.yaml` directly.

`lookback_days` skips dated articles older than the window, so a new RSS or HF source only backfills the last week. HTML scrapes have no dates, so a new HTML source processes up to `max_articles_per_run` on its first run unless its current URLs are seeded into `state.json`.

Interconnects is configured but blocked by Zscaler ("General AI and ML Applications" category) as of Sep 30, 2026. It logs an error each run until the block is lifted, then starts working with no change needed.

## Scheduling (daily automation)

Runs twice daily via launchd, not cron. Plists live at:

- `~/Library/LaunchAgents/com.newsagent.morning.plist` (6:00 AM)
- `~/Library/LaunchAgents/com.newsagent.afternoon.plist` (2:00 PM)

Both pin `WorkingDirectory` to the project root and call the venv's interpreter directly. Logs go to `~/news_agent.log`. After editing a plist, reload with `launchctl unload <path> && launchctl load <path>`. See `bootstrap-sean-projects.md` for the full migration recipe.
