"""Step 2c: fetch the RSS feeds and save new articles into the database.

Run from the backend folder:  python ingest.py
Safe to re-run: articles whose URL is already stored are skipped.
"""

import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import httpx

from db import get_connection
# Reuse the feed list, request settings and date helper from Step 1.
from ingest_preview import FEEDS, HEADERS, TIMEOUT_SECONDS, published_utc

SNIPPET_MAX_CHARS = 300

# Query parameters that only track clicks and don't change the page.
TRACKING_PREFIXES = ("utm_", "at_")
TRACKING_NAMES = {"fbclid", "gclid"}


def clean_url(url):
    """Remove tracking parameters and the #fragment, keep everything else."""
    parts = urlsplit(url.strip())
    # Split "?a=1&b=2" into pairs and keep only the non-tracking ones.
    kept = [
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if not name.lower().startswith(TRACKING_PREFIXES)
        and name.lower() not in TRACKING_NAMES
    ]
    # Rebuild the URL with the kept parameters and an empty fragment.
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), ""))


def make_snippet(description):
    """Turn a feed description into short plain text, or None if empty."""
    text = re.sub(r"<[^>]+>", " ", description or "")  # drop HTML tags
    text = html.unescape(text)                           # "&amp;" -> "&"
    text = " ".join(text.split())                        # collapse whitespace
    text = text[:SNIPPET_MAX_CHARS].rstrip()             # keep it short
    return text or None


def fetch_articles(source, url):
    """Download one feed and return a list of article dicts ready to store."""
    response = httpx.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS, follow_redirects=True)
    response.raise_for_status()  # treat 4xx/5xx as a failure
    feed = feedparser.parse(response.content)

    articles = []
    for entry in feed.entries:
        link = entry.get("link")
        if not link:
            continue  # can't store an article without a URL
        # Only metadata and a short snippet. We never store the article body.
        articles.append({
            "source": source,
            "title": entry.get("title", "(no title)").strip(),
            "url": clean_url(link),
            "snippet": make_snippet(entry.get("summary")),
            "published_at": published_utc(entry),
        })
    return articles


INSERT_SQL = """
    INSERT INTO articles (source, title, url, snippet, published_at)
    VALUES (%(source)s, %(title)s, %(url)s, %(snippet)s, %(published_at)s)
    ON CONFLICT (url) DO NOTHING
"""


def main():
    all_articles = []
    for source, url in FEEDS:
        try:
            all_articles.extend(fetch_articles(source, url))
        except Exception as error:
            # One bad feed should not stop the others.
            print(f"ERROR fetching {source} ({url}): {type(error).__name__}: {error}")

    inserted = 0
    with get_connection() as conn:
        for article in all_articles:
            cursor = conn.execute(INSERT_SQL, article)
            # rowcount is 1 if the row was added, 0 if the URL already existed.
            inserted += cursor.rowcount
        total = conn.execute("SELECT count(*) FROM articles").fetchone()[0]

    print(f"items fetched:         {len(all_articles)}")
    print(f"new rows inserted:     {inserted}")
    print(f"skipped (already had): {len(all_articles) - inserted}")
    print(f"total rows in table:   {total}")


if __name__ == "__main__":
    main()
