"""Step 4d: group articles about the same story, in memory, and print the result.

Run from the backend folder:  python cluster_preview.py
Read-only: it only SELECTs, it never changes the database.
"""

import sys
from collections import Counter
from datetime import timezone

import numpy as np
from pgvector.psycopg import register_vector
from sklearn.cluster import AgglomerativeClustering

from db import get_connection

# Print non-English letters (e.g. "Flávio") correctly in the Windows console.
sys.stdout.reconfigure(encoding="utf-8")

THRESHOLDS = [0.60, 0.55, 0.50, 0.45]  # minimum similarity to be "same story"
DETAIL_THRESHOLD = 0.55                 # print every cluster for this one
MAX_HOURS_APART = 72
MIN_TITLE_WORDS = 4                     # shorter titles are program labels
MAX_CLUSTERS_SHOWN = 30
LARGE_CLUSTER = 6                       # flag clusters this big for a look
TITLE_MAX_CHARS = 80

ARTICLES_SQL = """
    SELECT id, source, title, published_at, embedding
    FROM articles
    WHERE embedding IS NOT NULL
      AND published_at IS NOT NULL
      AND published_at >= now() - interval '30 days'
    ORDER BY id
"""


def can_cluster(article):
    """arXiv papers and very short titles always stay on their own."""
    _id, source, title, _published, _embedding = article
    return source != "arXiv" and len(title.split()) >= MIN_TITLE_WORDS


def distance_matrix(articles):
    """distance[i][j] = 1 - cosine similarity, or 1.0 if too far apart in time."""
    # One row of 384 numbers per article (pgvector gives Vector objects).
    vectors = np.array([a[4].to_numpy() for a in articles])
    # The vectors were saved with length 1, so a dot product is the cosine similarity.
    similarity = vectors @ vectors.T
    distance = np.clip(1 - similarity, 0, None)  # tiny negatives from rounding -> 0
    np.fill_diagonal(distance, 0)                 # every article is 0 from itself

    # Hours between every pair of articles.
    hours = np.array([a[3].timestamp() / 3600 for a in articles])
    hours_apart = np.abs(hours[:, None] - hours[None, :])
    distance[hours_apart > MAX_HOURS_APART] = 1.0  # never merge these
    return distance


def cluster(distance, threshold):
    """Return one cluster label per article. Same label = same story."""
    if len(distance) < 2:
        return np.zeros(len(distance), dtype=int)  # nothing to group
    model = AgglomerativeClustering(
        metric="precomputed",      # we pass our own distances
        linkage="average",         # distance between groups = average pair distance
        n_clusters=None,           # let the threshold decide how many groups
        distance_threshold=1 - threshold,
    )
    return model.fit_predict(distance)


def short(title):
    """Cut a title to TITLE_MAX_CHARS characters."""
    if len(title) <= TITLE_MAX_CHARS:
        return title
    return title[:TITLE_MAX_CHARS - 3] + "..."


def main():
    with get_connection() as conn:
        # Teach psycopg to read pgvector columns as numpy arrays.
        register_vector(conn)
        articles = conn.execute(ARTICLES_SQL).fetchall()

    clusterable = [a for a in articles if can_cluster(a)]
    alone = len(articles) - len(clusterable)  # each of these is its own story
    distance = distance_matrix(clusterable)
    print(f"loaded {len(articles)} articles: {len(clusterable)} clusterable, "
          f"{alone} kept on their own (arXiv or short title)")
    print()

    detail_groups = None
    for threshold in THRESHOLDS:
        labels = cluster(distance, threshold)
        # Collect the articles of each cluster label into a list.
        groups = {}
        for article, label in zip(clusterable, labels):
            groups.setdefault(label, []).append(article)

        sizes = [len(members) for members in groups.values()]
        stories = len(groups) + alone
        multi = sum(1 for s in sizes if s >= 2)
        largest = max(sizes, default=0)
        print(f"threshold {threshold:.2f}: {len(articles)} articles, {stories} stories, "
              f"{multi} clusters with 2+, largest {largest}  "
              f"({len(articles)} articles -> {stories} stories)")

        if threshold == DETAIL_THRESHOLD:
            detail_groups = groups

    # Print the clusters with 2+ articles at the detail threshold, largest first.
    multi_groups = [m for m in detail_groups.values() if len(m) >= 2]
    multi_groups.sort(key=len, reverse=True)
    print()
    print(f"=== clusters with 2+ articles at {DETAIL_THRESHOLD:.2f} "
          f"({len(multi_groups)} total, showing {min(len(multi_groups), MAX_CLUSTERS_SHOWN)}) ===")
    for members in multi_groups[:MAX_CLUSTERS_SHOWN]:
        sources = Counter(m[1] for m in members)
        flag = "  CHECK: large" if len(members) >= LARGE_CLUSTER else ""
        print()
        print(f"size {len(members)}, {len(sources)} source(s){flag}")
        for _id, source, title, published, _embedding in sorted(members, key=lambda m: m[3]):
            # Show the time in UTC, without seconds.
            when = published.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
            print(f"    {source:<11} | {when} | {short(title)}")


if __name__ == "__main__":
    main()
