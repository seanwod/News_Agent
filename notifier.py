"""Send a Slack notification summarising what the agent found."""

import os
from datetime import date

import requests


def notify_slack(results: list[dict]) -> None:
    """Post a digest message to Slack. Silently skips if no webhook is configured."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url or not results:
        return

    today = date.today().strftime("%b %-d, %Y")
    lines = [f"*News Agent Digest — {today}* ({len(results)} new article{'s' if len(results) != 1 else ''})\n"]

    for a in results:
        title = a.get("title", "Untitled")
        category = a.get("category", "")
        url = a.get("url", "")
        summary = a.get("summary", "")
        tag = f"[{category}]" if category else ""
        link = f"<{url}|{title}>" if url else title
        lines.append(f"• {link} {tag}")
        if summary:
            lines.append(f"  _{summary}_")

    payload = {"text": "\n".join(lines)}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        print(f"Slack notification failed: {exc}")
