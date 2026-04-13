"""Track which article URLs have already been processed to avoid duplicates."""

import json
from pathlib import Path

STATE_FILE = Path(__file__).parent / "state.json"
MAX_URLS = 10_000  # cap to prevent unbounded growth


def load_seen_urls() -> set[str]:
    if not STATE_FILE.exists():
        return set()
    with open(STATE_FILE) as f:
        return set(json.load(f).get("seen_urls", []))


def mark_seen(urls: list[str]) -> None:
    seen = load_seen_urls()
    seen.update(urls)
    if len(seen) > MAX_URLS:
        seen = set(list(seen)[-MAX_URLS:])
    with open(STATE_FILE, "w") as f:
        json.dump({"seen_urls": sorted(seen)}, f, indent=2)
