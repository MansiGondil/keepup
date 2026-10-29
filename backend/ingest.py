"""Fetch the RSS feeds and save new articles into the database.

Run from the backend folder:  python ingest.py
Safe to re-run: articles whose URL is already stored are skipped.
Every run (even a crashed one) is logged as one row in pipeline_runs.
"""

import html
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import httpx
from psycopg.types.json import Jsonb

from db import get_connection
# Reuse the feed list, request settings and date helper from Step 1.
from ingest_preview import FEEDS, HEADERS, TIMEOUT_SECONDS, published_utc

SNIPPET_MAX_CHARS = 300
ERROR_MAX_CHARS = 500

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
    # Hacker News descriptions are just a "Comments" link, which isn't a snippet.
    if text == "Comments":
        return None
    return text or None


def safe_error_text(error):
    """Short error text that is safe to store: no password, max 500 chars."""
    text = f"{type(error).__name__}: {error}"
    # We never build a connection string, but hide the password just in case.
    password = os.environ.get("POSTGRES_PASSWORD")
    if password:
        text = text.replace(password, "***")
    return text[:ERROR_MAX_CHARS]


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


LOG_SQL = """
    INSERT INTO pipeline_runs (started_at, finished_at, ok, duration_seconds,
                               items_fetched, new_rows, skipped, sources, error_message)
    VALUES (%(started_at)s, %(finished_at)s, %(ok)s, %(duration_seconds)s,
            %(items_fetched)s, %(new_rows)s, %(skipped)s, %(sources)s, %(error_message)s)
    RETURNING id
"""


def log_run(run):
    """Save one row about this run into pipeline_runs and return its id."""
    with get_connection() as conn:
        return conn.execute(LOG_SQL, run).fetchone()[0]


def main():
    # Everything we want to remember about this run. Filled in as we go.
    run = {
        "started_at": datetime.now(timezone.utc),
        "ok": False,
        "items_fetched": None,
        "new_rows": None,
        "skipped": None,
        "sources": [],
        "error_message": None,
    }
    start = time.monotonic()  # a stopwatch for the duration

    try:
        all_articles = []
        for source, url in FEEDS:
            try:
                articles = fetch_articles(source, url)
                all_articles.extend(articles)
                run["sources"].append({"feed": url, "items": len(articles), "error": None})
            except Exception as error:
                # One bad feed should not stop the others. Note it and move on.
                print(f"ERROR fetching {source} ({url}): {type(error).__name__}: {error}")
                run["sources"].append({"feed": url, "items": 0, "error": safe_error_text(error)})
        run["items_fetched"] = len(all_articles)

        inserted = 0
        with get_connection() as conn:
            for article in all_articles:
                cursor = conn.execute(INSERT_SQL, article)
                # rowcount is 1 if the row was added, 0 if the URL already existed.
                inserted += cursor.rowcount
            total = conn.execute("SELECT count(*) FROM articles").fetchone()[0]
        # Only set these after the inserts were saved.
        run["new_rows"] = inserted
        run["skipped"] = len(all_articles) - inserted
        run["ok"] = True

        print(f"items fetched:         {len(all_articles)}")
        print(f"new rows inserted:     {inserted}")
        print(f"skipped (already had): {len(all_articles) - inserted}")
        print(f"total rows in table:   {total}")
    except Exception as error:
        # The whole run crashed: remember why, then let the error continue.
        run["error_message"] = safe_error_text(error)
        raise
    finally:
        # This part runs whether the run worked or crashed.
        run["finished_at"] = datetime.now(timezone.utc)
        run["duration_seconds"] = round(time.monotonic() - start, 3)
        run["sources"] = Jsonb(run["sources"])  # store the list as JSON
        try:
            run_id = log_run(run)
            print(f"run #{run_id} logged")
        except Exception as log_error:
            # E.g. the database is down, so we can't log either.
            print(f"could not log run: {safe_error_text(log_error)}")


if __name__ == "__main__":
    main()
