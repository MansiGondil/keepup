"""Step 6a: export a sample of articles to a CSV sheet for hand-labeling topics.

Run from the backend folder:  python export_label_sheet.py
Use --force to replace an existing sheet (this DELETES your labels in it).
Read-only for the database: it only SELECTs.
"""

import argparse
import csv
import random
import sys
from collections import Counter
from pathlib import Path

from db import BACKEND_DIR, get_connection

# Print non-English letters correctly in the Windows console.
sys.stdout.reconfigure(encoding="utf-8")

SHEET_PATH = BACKEND_DIR.parent / "data" / "labels" / "labeling_sheet.csv"

# How many articles to take from each source.
SAMPLE_SIZES = {"Hacker News": 40, "BBC News": 20, "arXiv": 15}

# A fixed seed means the same database gives the same sample every time.
SEED = 42

COLUMNS = ["id", "source", "title", "snippet", "url", "topics"]


def fetch_articles(conn, source):
    """Return every article from one source, oldest id first."""
    return conn.execute(
        "SELECT id, source, title, snippet, url FROM articles "
        "WHERE source = %s ORDER BY id",
        (source,),
    ).fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing sheet (loses your labels)")
    args = parser.parse_args()

    # Safety check: the sheet holds hand-made labels, so never replace it
    # by accident.
    if SHEET_PATH.exists() and not args.force:
        print(f"{SHEET_PATH} already exists, so nothing was written.")
        print("It may contain your labels. Run with --force to replace it.")
        sys.exit(1)

    rng = random.Random(SEED)
    rows = []
    with get_connection() as conn:
        for source, size in SAMPLE_SIZES.items():
            articles = fetch_articles(conn, source)
            # Take all of them if the source has fewer than we asked for.
            rows.extend(rng.sample(articles, min(size, len(articles))))

    # Mix the sources so the sheet doesn't show all of one source in a row.
    rng.shuffle(rows)

    SHEET_PATH.parent.mkdir(parents=True, exist_ok=True)
    # "utf-8-sig" adds a BOM, which tells Excel the file is UTF-8.
    # newline="" stops the csv module from writing blank lines on Windows.
    with open(SHEET_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for article_id, source, title, snippet, url in rows:
            writer.writerow([article_id, source, title, snippet or "", url, ""])

    print(f"Wrote {len(rows)} rows to {SHEET_PATH}")
    for source, count in Counter(row[1] for row in rows).items():
        print(f"  {source}: {count}")


if __name__ == "__main__":
    main()
