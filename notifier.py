"""Post the digest to Slack."""

import os
from datetime import date

import requests

MAX_CHARS = 12_000  # split long digests; Slack truncates a message at 40k characters


def notify_slack(results: list[dict]) -> bool:
    """Post a digest to Slack, grouped by site. Returns True if every message posted."""
    if not results:
        return True
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()

    today = date.today().strftime("%b %-d, %Y")
    header = f"*News Agent Digest: {today}* ({len(results)} new article{'s' if len(results) != 1 else ''})\n"

    by_site: dict[str, list[dict]] = {}
    for a in results:
        by_site.setdefault(a.get("site", "Other"), []).append(a)

    sections = []
    for site, articles in by_site.items():
        lines = [f"\n*{site}*"]
        for a in articles:
            title = a.get("title", "Untitled")
            url = a.get("url", "")
            link = f"<{url}|{title}>" if url else title
            category = f" [{a['category']}]" if a.get("category") else ""
            lines.append(f"• {link}{category}")
            if a.get("summary"):
                lines.append(f"  _{a['summary']}_")
        sections.append("\n".join(lines) + "\n")

    messages = [header]
    for section in sections:
        if len(messages[-1]) + len(section) > MAX_CHARS:
            messages.append("")
        messages[-1] += section

    for text in messages:
        try:
            resp = requests.post(webhook_url, json={"text": text}, timeout=10)
            resp.raise_for_status()
        except Exception as exc:
            print(f"Slack post failed: {exc}")
            return False
    return True
