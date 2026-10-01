# Bootstrap, News Agent

> Read this first when picking up the project on a new Mac or in a new IDE.
> Owner: Sean O'Donoghue. Last refreshed: 2026-09-30.

## 1. 60-second sanity check

Paste this block. If it succeeds, the project is alive on this machine.

```bash
cd /Users/odonog/Desktop/seanailab/News_Agent
/usr/local/bin/python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python cli.py sites list
```

`sites list` should print the configured sources (19 as of 2026-09-30). If it fails, jump to §2 (runtime) or §3 (deps) depending on the error.

## 2. Runtime requirements

- **Language:** Python 3.14 (3.14.5 confirmed working). Not pinned in repo; install via Homebrew (`brew install python@3.14`) or Python.org installer.
- **Interpreter path on this Mac:** `/usr/local/bin/python3`. There is also `/opt/homebrew/bin/python3` (Apple Silicon Homebrew) on macOS systems. Pick one and stay with it. The launchd plist uses `/Users/odonog/Desktop/seanailab/News_Agent/venv/bin/python3`, which resolves through the venv to whichever base Python created it.
- **OS notes:**
  - Scheduled runs use launchd (not cron). One plist at `~/Library/LaunchAgents/com.newsagent.scheduler.plist`, firing hourly, with `WorkingDirectory` pinned to the project root.
  - Corporate Zscaler SSL MITM breaks `pip` and `requests` without a fix. `pip-system-certs` is in `requirements.txt` precisely to read certs from the macOS keychain. Do not remove it.
- **System binaries required:** none beyond Python.

## 3. Dependencies

- **Manifest:** `requirements.txt`
- **Install command:** `pip install -r requirements.txt` (inside the venv)
- **Convention:** venv at `./venv` (gitignored). Recreate fresh on every new machine.

Current pinned deps:

```
anthropic>=0.40.0
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
| `SLACK_WEBHOOK_URL` | Yes | api.slack.com/apps → News Agent → Incoming Webhooks → the `#sean-ai-news` webhook. | The run exits before fetching anything. Slack is the only output. |

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

- **Notion (retired 2026-09-30).** The agent no longer writes to Notion. The old "News Agent Digest" database (Sean's Personal → Top Of Mind) keeps its history but is not updated.

- **Slack**
  - Login: Security Benefit workspace. Target is `#sean-ai-news`, a private channel with Sean as the only member, set to notify on all new messages.
  - Role: self.
  - Dashboard: https://api.slack.com/apps
  - Verify access without posting: `curl -X POST -H 'Content-type: application/json' --data '{}' "$SLACK_WEBHOOK_URL"` should return `invalid_payload`. A dead webhook returns `no_service` or `invalid_token`.

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
| Smoke test (no Slack post) | None today. Closest is `python -c "from scraper import fetch_articles; from agent import load_config; print(len(fetch_articles(load_config()['sites'][0])))"` |
| Tail launchd log | `tail -f ~/news_agent.log` |

There is no test suite. The smoke test is "verbose run, see the digest arrive in `#sean-ai-news`."

## 8. Production / deployment

- **Where it runs:** locally on Sean's Mac via launchd. No cloud deploy.
- **Schedule:** digests at 6:00 AM and 2:00 PM Mac local time (`settings.run_hours` in `config.yaml`). `com.newsagent.scheduler` fires every hour on the hour and runs `cli.py run --scheduled`, which exits quietly unless a slot has passed since the last scheduled run.
- **Manual trigger:** `python cli.py run` (always runs, does not touch the schedule). `launchctl kickstart gui/$(id -u)/com.newsagent.scheduler` tests the launchd path, but it only posts if a slot is due.
- **Reload the plist after editing:** `launchctl unload ~/Library/LaunchAgents/com.newsagent.scheduler.plist && launchctl load ~/Library/LaunchAgents/com.newsagent.scheduler.plist`.
- **Logs:** `~/news_agent.log` (combined stdout + stderr from both jobs).
- **Last known healthy:** 2026-09-30. Webhook moved to `#sean-ai-news`; test post confirmed in the channel.

## 9. Live state, where to look

- **Repo:** https://github.com/seanwod/News_Agent
- **Digest:** `#sean-ai-news` (private Slack channel), posted by the News Agent incoming webhook. Digests before 2026-09-30 1:40 PM went to Sean's DM with himself.
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

# 5. Smoke test: verbose run (will hit the sources, Anthropic, and Slack)
python cli.py run --verbose

# 6. Confirm the digest arrived in #sean-ai-news.

# 7. Install the launchd schedule. Copy com.newsagent.scheduler.plist from your
#    old Mac, or recreate it (hourly StartCalendarInterval with only Minute=0,
#    ProgramArguments: venv python3, cli.py, run, --scheduled) with
#    WorkingDirectory pointing at the new path. Then:
launchctl load ~/Library/LaunchAgents/com.newsagent.scheduler.plist
launchctl list | grep newsagent   # should show com.newsagent.scheduler
```

## 11. Gotchas / project-specific quirks

- **Empty `state.json` will flood Slack on the next run.** State is gitignored, so cloning to a new machine starts with no memory of what was already processed. Before the first real run on a new machine, copy `state.json` over from the old machine, or accept a one-time backfill. Dated sources (RSS, Hugging Face) only backfill `lookback_days` (7); undated HTML sources backfill up to `max_articles_per_run` (10) each. The 2026-05-26 migration hit this exact issue: 20 articles got reposted because state was empty.
- **launchd needs absolute paths.** `WorkingDirectory` is required in the plist. Without it, the venv's `python` can't find `cli.py` and `load_dotenv` can't find `.env`. Both currently set correctly.
- **Don't use `/usr/bin/env python3` in plists.** launchd's PATH differs from the login shell. The plist pins the venv's interpreter directly, which is the right pattern. Keep it.
- **Zscaler SSL MITM is why `pip-system-certs` is in requirements.txt.** Without it, `pip install` from inside Security Benefit's network breaks on TLS verification. Don't remove this dep even if it looks unused. It patches certs at import time.
- **`.env` empty values don't override shell env.** Per Sean's CLAUDE.md, the standard guard is `value = value or os.environ.get("KEY")`. This project uses `python-dotenv` with `override=True`, which means `.env` always wins. If you ever export `ANTHROPIC_API_KEY` in your shell and forget to update `.env`, the shell value gets ignored. Keep `.env` authoritative.
- **Never schedule clock times in launchd directly.** launchd keeps the time zone it booted with. After the Mac moved from Eastern to Pacific on 2026-09-28 without a reboot, the old 6 AM / 2 PM plists fired at 3 AM / 11 AM Pacific. The hourly job plus `run --scheduled` reads the current local time on every run, so travel no longer shifts the digest.
- **Several sources share one `label` on purpose.** xAI and Cursor both post under "SpaceX AI", three Gemma sources under "Gemma (Google)", and The Decoder, SCMP, and Recode under "Open-weight news". The label is the Slack heading.
- **Zscaler blocks most AI lab websites** (DeepSeek, Qwen, Kimi, Z.ai, Xiaomi MiMo, Google DeepMind, Interconnects). The open-weight labs are tracked through their Hugging Face orgs instead. Interconnects is configured and logs a 403 each run until the block is lifted.
- **`max_articles_per_run` is per-site, not total.** Default 10. `lookback_days` keeps normal runs to a handful of articles.
- **The HTML scraper auto-skips the index page itself** (anything ending in `/news` or `/research`). If you add a new site whose article URLs end in those paths, that filter will eat them. See `_fetch_from_html` in `scraper.py`.
