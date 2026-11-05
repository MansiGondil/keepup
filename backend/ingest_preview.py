"""Step 1: fetch a few RSS feeds and print the 10 newest items.

Run from the backend folder:  python ingest_preview.py
"""

from datetime import datetime, timezone

import feedparser
import httpx

from feeds import FEEDS, HEADERS, TIMEOUT_SECONDS

HOW_MANY = 10


def published_utc(entry):
    """Return the item's published time as a UTC datetime, or None if missing."""
    # feedparser turns the date text into a time tuple (already in UTC).
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is None:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)


def fetch_items(source, url):
    """Download one feed and return a list of small item dicts."""
    response = httpx.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS, follow_redirects=True)
    response.raise_for_status()  # treat 4xx/5xx as a failure
    feed = feedparser.parse(response.content)

    items = []
    for entry in feed.entries:
        # Keep only the fields we print. We never keep the article body.
        items.append({
            "title": entry.get("title", "(no title)").strip(),
            "source": source,
            "published": published_utc(entry),
            "link": entry.get("link", ""),
        })
    return items


def main():
    all_items = []

    for feed in FEEDS:
        try:
            all_items.extend(fetch_items(feed["name"], feed["url"]))
        except Exception as error:
            # One bad feed should not stop the others.
            label = f"{feed['name']} / {feed['section']}"
            print(f"ERROR fetching {label} ({feed['url']}): {type(error).__name__}: {error}")

    # Items without a date can't be ranked by time, so skip them.
    dated = [item for item in all_items if item["published"] is not None]

    # Newest first, then keep the top 10.
    dated.sort(key=lambda item: item["published"], reverse=True)

    for number, item in enumerate(dated[:HOW_MANY], start=1):
        print(f"{number}. {item['title']}")
        print(f"   source:    {item['source']}")
        print(f"   published: {item['published'].isoformat()}")
        print(f"   link:      {item['link']}")
        print()


if __name__ == "__main__":
    main()
