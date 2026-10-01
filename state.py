"""Track which article URLs have already been processed, and when the last scheduled run happened."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).parent / "state.json"
MAX_URLS = 10_000  # cap to prevent unbounded growth


def _load() -> dict:
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)


def _save(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_seen_urls() -> set[str]:
    return set(_load().get("seen_urls", []))


def mark_seen(urls: list[str]) -> None:
    state = _load()
    seen = set(state.get("seen_urls", []))
    seen.update(urls)
    if len(seen) > MAX_URLS:
        seen = set(list(seen)[-MAX_URLS:])
    state["seen_urls"] = sorted(seen)
    _save(state)


def load_last_scheduled_run() -> datetime | None:
    value = _load().get("last_scheduled_run")
    return datetime.fromisoformat(value) if value else None


def record_scheduled_run(when: datetime) -> None:
    """Store a timezone-aware time, so comparisons stay correct after a time zone change."""
    state = _load()
    state["last_scheduled_run"] = when.isoformat()
    _save(state)
