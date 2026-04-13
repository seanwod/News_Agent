"""Write article summaries to the Notion database."""

import os
from datetime import date

from notion_client import Client


def write_article(article: dict) -> str:
    """Create a page in the Notion database for one article. Returns the Notion page URL."""
    client = Client(auth=os.environ["NOTION_API_KEY"])
    database_id = os.environ["NOTION_DATABASE_ID"]

    article_date = article.get("date") or date.today().isoformat()
    # Notion DATE properties only accept ISO-8601 date strings (YYYY-MM-DD)
    if "T" in str(article_date):
        article_date = str(article_date).split("T")[0]

    response = client.pages.create(
        parent={"database_id": database_id},
        properties={
            "Title": {"title": [{"text": {"content": article["title"][:200]}}]},
            "Date": {"date": {"start": article_date}},
            "Site": {"select": {"name": article.get("site", "Other")}},
            "Category": {"select": {"name": article.get("category", "Other")}},
            "Summary": {
                "rich_text": [{"text": {"content": article.get("summary", "")[:2000]}}]
            },
            "URL": {"url": article.get("url") or None},
        },
    )
    return response.get("url", "")
