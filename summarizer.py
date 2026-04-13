"""Summarize articles using Claude."""

import anthropic

VALID_CATEGORIES = {"Blog Post", "Research Paper", "Product Update", "News", "Other"}


def summarize_article(title: str, content: str, site_name: str) -> dict:
    """Return {summary, category} for an article using Claude."""
    client = anthropic.Anthropic()

    prompt = f"""Summarize the following article from {site_name} for a morning briefing digest.

Article Title: {title}

Article Content:
{content[:3000]}

Respond in exactly this format (no extra text):
SUMMARY: <2-3 sentence summary of the key points>
CATEGORY: <one of: Blog Post, Research Paper, Product Update, News, Other>"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    summary = ""
    category = "Other"

    for line in response_text.strip().split("\n"):
        if line.startswith("SUMMARY:"):
            summary = line[len("SUMMARY:"):].strip()
        elif line.startswith("CATEGORY:"):
            raw = line[len("CATEGORY:"):].strip()
            category = raw if raw in VALID_CATEGORIES else "Other"

    return {"summary": summary, "category": category}
