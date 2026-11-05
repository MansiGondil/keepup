"""Step 4c: print possible duplicate pairs so a human can judge them.

Run from the backend folder:  python dup_candidates.py
Read-only: it only SELECTs, it never changes the database.
"""

from db import get_connection

# Similarity bands, highest first: (label, lowest similarity, highest similarity).
# A pair belongs to a band if low <= similarity < high.
BANDS = [
    ("0.85+", 0.85, 1.01),
    ("0.75-0.85", 0.75, 0.85),
    ("0.65-0.75", 0.65, 0.75),
    ("0.55-0.65", 0.55, 0.65),
]
PAIRS_PER_BAND = 8
TITLE_MAX_CHARS = 80

# Every pair of articles (a.id < b.id, so each pair appears once) that:
# - both have an embedding and a published time
# - neither comes from arXiv
# - were published within 72 hours of each other
# - are at least as similar as the lowest band.
# "<=>" is pgvector's cosine distance; similarity = 1 - distance.
PAIRS_SQL = """
    SELECT
        1 - (a.embedding <=> b.embedding)                         AS similarity,
        abs(extract(epoch FROM a.published_at - b.published_at)) / 3600
                                                                  AS gap_hours,
        a.source, a.title, b.source, b.title
    FROM articles a
    JOIN articles b ON a.id < b.id
    WHERE a.embedding IS NOT NULL AND b.embedding IS NOT NULL
      AND a.published_at IS NOT NULL AND b.published_at IS NOT NULL
      AND a.source <> 'arXiv' AND b.source <> 'arXiv'
      AND abs(extract(epoch FROM a.published_at - b.published_at)) <= 72 * 3600
      AND 1 - (a.embedding <=> b.embedding) >= %s
    ORDER BY similarity DESC
"""


def pick_evenly(items, how_many):
    """Pick up to how_many items spread evenly from first to last."""
    if len(items) <= how_many:
        return items
    # E.g. 100 items, 8 picks -> positions 0, 14, 28, ... 99.
    step = (len(items) - 1) / (how_many - 1)
    return [items[round(i * step)] for i in range(how_many)]


def short(title):
    """Cut a title to TITLE_MAX_CHARS characters."""
    if len(title) <= TITLE_MAX_CHARS:
        return title
    return title[:TITLE_MAX_CHARS - 3] + "..."


def main():
    lowest = min(low for _label, low, _high in BANDS)
    with get_connection() as conn:
        pairs = conn.execute(PAIRS_SQL, (lowest,)).fetchall()

    # Count first, so the totals are easy to see at the top.
    print("pairs per band:")
    for label, low, high in BANDS:
        count = sum(1 for p in pairs if low <= p[0] < high)
        print(f"  {label:>10}: {count}")

    for label, low, high in BANDS:
        in_band = [p for p in pairs if low <= p[0] < high]
        print()
        print(f"=== {label} ({len(in_band)} pairs, showing {min(len(in_band), PAIRS_PER_BAND)}) ===")
        for similarity, gap_hours, source_a, title_a, source_b, title_b in pick_evenly(in_band, PAIRS_PER_BAND):
            print(f"{similarity:.2f}  gap {float(gap_hours):5.1f}h")
            print(f"    {source_a:<11} | {short(title_a)}")
            print(f"    {source_b:<11} | {short(title_b)}")


if __name__ == "__main__":
    main()
