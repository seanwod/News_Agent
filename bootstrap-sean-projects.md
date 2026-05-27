# Bootstrap, News Agent

> Read this first when picking up the project on a new Mac or in a new IDE.
> Owner: Sean O'Donoghue. Last refreshed: 2026-05-26.

## 1. 60-second sanity check

Paste this block. If it succeeds, the project is alive on this machine.

```bash
cd /Users/odonog/Desktop/seanailab/News_Agent
/usr/local/bin/python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python cli.py sites list
```

`sites list` should print the two configured sources (Anthropic, Anthropic Research). If it fails, jump to §2 (runtime) or §3 (deps) depending on the error.

## 2. Runtime requirements

- **Language:** Python 3.14 (3.14.5 confirmed working). Not pinned in repo; install via Homebrew (`brew install python@3.14`) or Python.org installer.
- **Interpreter path on this Mac:** `/usr/local/bin/python3`. There is also `/opt/homebrew/bin/python3` (Apple Silicon Homebrew) on macOS systems. Pick one and stay with it. The launchd plists use `/Users/odonog/Desktop/seanailab/News_Agent/venv/bin/python3`, which resolves through the venv to whichever base Python created it.
- **OS notes:**
  - Scheduled runs use launchd (not cron). Plists at `~/Library/LaunchAgents/com.newsagent.morning.plist` and `~/Library/LaunchAgents/com.newsagent.afternoon.plist`. Both pin `WorkingDirectory` to the project root.
  - Corporate Zscaler SSL MITM breaks `pip` and `requests` without a fix. `pip-system-certs` is in `requirements.txt` precisely to read certs from the macOS keychain. Do not remove it.
- **System binaries required:** none beyond Python.

## 3. Dependencies

- **Manifest:** `requirements.txt`
- **Install command:** `pip install -r requirements.txt` (inside the venv)
- **Convention:** venv at `./venv` (gitignored). Recreate fresh on every new machine.

Current pinned deps:

```
anthropic>=0.40.0
notion-client>=2.2.0
feedparser>=6.0.11
requests>=2.31.0
beautifulsoup4>=4.12.0
click>=8.1.0
python-dotenv>=1.0.0
pyyaml>=6.0.0
pip-system-certs>=4.0
```

## 4. Environment variables

The variable list is sourced from `.env.example`. Real values live in `.env` (gitignored, never committed, never in this doc).

| Variable | Required? | Where to get the value | What breaks without it |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | console.anthropic.com under the Security Benefit org. Settings → API Keys → Create Key. | Summarizer fails on every article. |
| `NOTION_API_KEY` | Yes | notion.so/profile/integrations (Sean's Personal workspace). Open the "News Agent" integration → copy the internal integration token. | Notion writes fail; nothing lands in the database. |
| `NOTION_DATABASE_ID` | Yes | Pre-set to `d423fe7ae84745c4b2538a2311ab56f6`. Already in `.env.example` and `config.yaml`. | Notion writes fail. |
| `SLACK_WEBHOOK_URL` | No | Slack → Apps → Incoming Webhooks → personal DM. Optional, agent runs without it (just no digest message). | No Slack digest. Articles still write to Notion. |

To create a fresh `.env` on a new machine:

```bash
cp .env.example .env
# Then edit .env in your IDE and paste in each value.
```

## 5. External services

- **Anthropic API**
  - Login: console.anthropic.com under the Security Benefit org seat.
  - Role: member (org-level access required to create keys).
  - Dashboard: https://console.anthropic.com
  - Verify access: `python -c "import anthropic; print(anthropic.Anthropic().messages.create(model='claude-opus-4-6', max_tokens=10, messages=[{'role':'user','content':'hi'}]).content[0].text)"`

- **Notion**
  - Login: Sean's Personal workspace (not Security Benefit).
  - Role: Owner.
  - Dashboard: https://www.notion.so → Sean's Personal → Top Of Mind → News Agent Digest.
  - Direct database link: https://www.notion.so/d423fe7ae84745c4b2538a2311ab56f6
  - Verify access: `python -c "import os; from notion_client import Client; from dotenv import load_dotenv; load_dotenv(); print(Client(auth=os.environ['NOTION_API_KEY']).databases.retrieve(os.environ['NOTION_DATABASE_ID'])['title'][0]['plain_text'])"`

- **Slack**
  - Login: personal workspace, DM target.
  - Role: self.
  - Dashboard: https://api.slack.com/apps
  - Verify access: `curl -X POST -H 'Content-type: application/json' --data '{"text":"ping from News Agent"}' "$SLACK_WEBHOOK_URL"` should return `ok`.

- **GitHub**
  - Login: personal account `seanwod`.
  - Role: Owner.
  - Repo: https://github.com/seanwod/News_Agent
  - Verify access: `gh repo view seanwod/News_Agent`

## 6. IDE setup

Works in both **VS Code** and **Cursor** (Cursor is a VS Code fork, configs are identical).

- **Recommended extensions:**
  - Python (ms-python.python), for interpreter selection and debugging.
  - Pylance (ms-python.vscode-pylance), for type hints across `cli.py`, `agent.py`, etc.
  - YAML (redhat.vscode-yaml), for `config.yaml`.
  - GitHub Pull Requests (GitHub.vscode-pull-request-github), since the repo is on GitHub.
- **Workspace settings to verify:**
  - Interpreter set to `./venv/bin/python` (Cmd-Shift-P → "Python: Select Interpreter").
  - Format on save: optional. The project has no formatter pinned.
- **Claude Code skills worth knowing here:**
  - `/run` to launch `python cli.py run --verbose` and watch end-to-end.
  - `/loop` if you want to babysit a scheduled run cycle.
  - `update-config` skill for adjusting `.claude/settings.local.json` permissions (already includes the launchd commands used during setup).

## 7. Run commands

| What | Command |
|---|---|
| List configured sites | `python cli.py sites list` |
| Add a site (RSS) | `python cli.py sites add "OpenAI" "https://openai.com/news" --rss "https://openai.com/news/rss"` |
| Add a site (HTML scrape) | `python cli.py sites add "Google DeepMind" "https://deepmind.google/discover/blog/"` |
| Remove a site | `python cli.py sites remove "OpenAI"` |
| Full run, quiet | `python cli.py run` |
| Full run, verbose | `python cli.py run --verbose` |
| Smoke test (no Notion write) | None today. Closest is `python -c "from scraper import fetch_articles; from agent import load_config; print(len(fetch_articles(load_config()['sites'][0])))"` |
| Tail launchd log | `tail -f ~/news_agent.log` |

There is no test suite. The smoke test is "verbose run on a Saturday morning, see articles appear in Notion."

## 8. Production / deployment

- **Where it runs:** locally on Sean's Mac via launchd. No cloud deploy.
- **Schedule:** twice daily.
  - `com.newsagent.morning` fires at 6:00 AM local time.
  - `com.newsagent.afternoon` fires at 2:00 PM local time.
- **Manual trigger:** `launchctl start com.newsagent.morning` (or `.afternoon`). Or just `python cli.py run`.
- **Reload plists after editing:** `launchctl unload ~/Library/LaunchAgents/com.newsagent.morning.plist && launchctl load ~/Library/LaunchAgents/com.newsagent.morning.plist`. Same for afternoon.
- **Logs:** `~/news_agent.log` (combined stdout + stderr from both jobs).
- **Last known healthy:** 2026-05-26. Test run wrote 20 articles to Notion.

## 9. Live state, where to look

- **Repo:** https://github.com/seanwod/News_Agent
- **Notion database:** https://www.notion.so/d423fe7ae84745c4b2538a2311ab56f6
- **Anthropic usage:** https://console.anthropic.com (Security Benefit org → Usage)
- **launchd job status:** `launchctl list | grep newsagent`
- **Run log:** `~/news_agent.log`
- **Local state (seen URLs):** `./state.json` (gitignored). If this file is deleted or empty, the next run will treat the most recent N articles per site as new and re-post them. See §11.

## 10. Health check after migration

Run these in order on a fresh machine. This is the recipe that worked on 2026-05-26.

```bash
# 1. Clone
git clone https://github.com/seanwod/News_Agent.git
cd News_Agent

# 2. Build venv with Python 3.14 (or whatever is current)
/usr/local/bin/python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Populate .env
cp .env.example .env
# Edit .env in your IDE, paste real values from password manager.

# 4. Smoke test: list sites (no API calls)
python cli.py sites list

# 5. Smoke test: verbose run (will hit Anthropic + Notion + Slack)
python cli.py run --verbose

# 6. Confirm articles landed in Notion (eye check the database).

# 7. Install launchd schedules. Copy the plists from your old Mac, or recreate
#    them with WorkingDirectory pointing at the new path. Then:
launchctl load ~/Library/LaunchAgents/com.newsagent.morning.plist
launchctl load ~/Library/LaunchAgents/com.newsagent.afternoon.plist
launchctl list | grep newsagent   # should show both labels
```

## 11. Gotchas / project-specific quirks

- **Empty `state.json` will flood Notion (and Slack) on the next run.** State is gitignored, so cloning to a new machine starts with no memory of what was already processed. Before the first real run on a new machine, copy `state.json` over from the old machine, or accept a one-time backfill of up to `max_articles_per_run` (default 10) per site. The 2026-05-26 migration hit this exact issue: 20 articles got reposted because state was empty.
- **launchd needs absolute paths.** `WorkingDirectory` is required in both plists. Without it, the venv's `python` can't find `cli.py` and `load_dotenv` can't find `.env`. Both currently set correctly.
- **Don't use `/usr/bin/env python3` in plists.** launchd's PATH differs from the login shell. The plists pin the venv's interpreter directly, which is the right pattern. Keep it.
- **Zscaler SSL MITM is why `pip-system-certs` is in requirements.txt.** Without it, `pip install` from inside Security Benefit's network breaks on TLS verification. Don't remove this dep even if it looks unused. It patches certs at import time.
- **`.env` empty values don't override shell env.** Per Sean's CLAUDE.md, the standard guard is `value = value or os.environ.get("KEY")`. This project uses `python-dotenv` with `override=True`, which means `.env` always wins. If you ever export `ANTHROPIC_API_KEY` in your shell and forget to update `.env`, the shell value gets ignored. Keep `.env` authoritative.
- **Two Anthropic feeds, one Notion label.** `config.yaml` sets `notion_label: Anthropic` for both the news and research feeds. This is intentional. The Notion "Site" select stays clean instead of fragmenting into "Anthropic" / "Anthropic Research".
- **Notion DATE properties only accept `YYYY-MM-DD`.** `notion_writer.py` strips any time component before writing. Don't change this; RSS feeds publish ISO-8601 datetimes that Notion otherwise rejects.
- **`max_articles_per_run` is per-site, not total.** Default 10. A 2-site config can produce up to 20 articles per run.
- **The HTML scraper auto-skips the index page itself** (anything ending in `/news` or `/research`). If you add a new site whose article URLs end in those paths, that filter will eat them. See `scraper.py:57-58`.
