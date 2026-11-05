"""Step 4e: group recent articles into stories and save them.

Run from the backend folder:  python cluster_stories.py
Safe to re-run: the same articles give the same story ids, and everything is
saved in one transaction (all or nothing).
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

SIMILARITY_THRESHOLD = 0.55  # minimum similarity to count as the same story
WINDOW_HOURS = 72            # articles further apart than this never merge
LOOKBACK_DAYS = 30           # older articles get no story
MIN_TITLE_WORDS = 4          # shorter titles are program labels ("Inside Health")

# Hacker News posts that are discussions, not news about an event.
STANDALONE_PREFIXES = ("ask hn:", "show hn:", "tell hn:", "launch hn:")

ARTICLES_SQL = """
    SELECT id, source, title, published_at, embedding, story_id
    FROM articles
    WHERE published_at IS NOT NULL
      AND published_at >= now() - make_interval(days => %s)
    ORDER BY id
"""

UPSERT_SQL = """
    INSERT INTO stories (id, headline, representative_article_id, first_published_at,
                         last_published_at, article_count, source_count)
    VALUES (%(id)s, %(headline)s, %(representative_article_id)s, %(first_published_at)s,
            %(last_published_at)s, %(article_count)s, %(source_count)s)
    ON CONFLICT (id) DO UPDATE SET
        headline                  = EXCLUDED.headline,
        representative_article_id = EXCLUDED.representative_article_id,
        first_published_at        = EXCLUDED.first_published_at,
        last_published_at         = EXCLUDED.last_published_at,
        article_count             = EXCLUDED.article_count,
        source_count              = EXCLUDED.source_count,
        updated_at                = now()
    -- Only touch the row if something actually changed.
    WHERE (stories.headline, stories.representative_article_id, stories.first_published_at,
           stories.last_published_at, stories.article_count, stories.source_count)
          IS DISTINCT FROM
          (EXCLUDED.headline, EXCLUDED.representative_article_id, EXCLUDED.first_published_at,
           EXCLUDED.last_published_at, EXCLUDED.article_count, EXCLUDED.source_count)
    RETURNING id
"""

# Articles outside the lookback lose their story.
CLEAR_OLD_SQL = """
    UPDATE articles SET story_id = NULL
    WHERE story_id IS NOT NULL
      AND (published_at IS NULL OR published_at < now() - make_interval(days => %s))
"""

SET_STORY_SQL = "UPDATE articles SET story_id = %s WHERE id = %s"

# Stories that no longer have any article.
DELETE_EMPTY_SQL = """
    DELETE FROM stories s
    WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.story_id = s.id)
    RETURNING id
"""


def can_cluster(article):
    """arXiv papers, very short titles, HN discussion posts and articles
    without an embedding always become their own story."""
    _id, source, title, _published, embedding, _story = article
    if source == "arXiv" or embedding is None:
        return False
    if len(title.split()) < MIN_TITLE_WORDS:
        return False
    return not title.strip().lower().startswith(STANDALONE_PREFIXES)


def distance_matrix(vectors, articles):
    """distance[i][j] = 1 - cosine similarity, or 1.0 if too far apart in time."""
    # The vectors were saved with length 1, so a dot product is the cosine similarity.
    similarity = vectors @ vectors.T
    distance = np.clip(1 - similarity, 0, None)  # tiny negatives from rounding -> 0
    np.fill_diagonal(distance, 0)                 # every article is 0 from itself

    # Hours between every pair of articles.
    hours = np.array([a[3].timestamp() / 3600 for a in articles])
    hours_apart = np.abs(hours[:, None] - hours[None, :])
    distance[hours_apart > WINDOW_HOURS] = 1.0    # never merge these
    return distance


def cluster(distance):
    """Return one cluster label per article. Same label = same story."""
    if len(distance) < 2:
        return np.zeros(len(distance), dtype=int)  # nothing to group
    model = AgglomerativeClustering(
        metric="precomputed",      # we pass our own distances
        linkage="average",         # distance between groups = average pair distance
        n_clusters=None,           # let the threshold decide how many groups
        distance_threshold=1 - SIMILARITY_THRESHOLD,
    )
    return model.fit_predict(distance)


def build_story(members, vectors_by_id):
    """Turn a list of member articles into one story dict."""
    # Earliest article first (ties broken by id), so the id is stable.
    members = sorted(members, key=lambda a: (a[3], a[0]))
    first = members[0]

    if len(members) == 1:
        representative = first
    else:
        # The headline comes from the member closest to the group's average meaning.
        vectors = np.array([vectors_by_id[a[0]] for a in members])
        mean = vectors.mean(axis=0)
        representative = members[int(np.argmax(vectors @ mean))]

    return {
        "id": f"st_{first[3].astimezone(timezone.utc):%Y%m%d}_{first[0]}",
        "headline": representative[2],
        "representative_article_id": representative[0],
        "first_published_at": first[3],
        "last_published_at": max(a[3] for a in members),
        "article_count": len(members),
        "source_count": len({a[1] for a in members}),
        "member_ids": [a[0] for a in members],
    }


def main():
    with get_connection() as conn:
        # Teach psycopg to read pgvector columns.
        register_vector(conn)
        articles = conn.execute(ARTICLES_SQL, (LOOKBACK_DAYS,)).fetchall()

        # --- 1. Group the articles (in memory, nothing saved yet) ---
        clusterable = [a for a in articles if can_cluster(a)]
        groups = [[a] for a in articles if not can_cluster(a)]  # one-article stories

        vectors_by_id = {a[0]: a[4].to_numpy() for a in clusterable}
        if clusterable:
            vectors = np.array([vectors_by_id[a[0]] for a in clusterable])
            labels = cluster(distance_matrix(vectors, clusterable))
            by_label = {}
            for article, label in zip(clusterable, labels):
                by_label.setdefault(label, []).append(article)
            groups.extend(by_label.values())

        stories = [build_story(members, vectors_by_id) for members in groups]

        # Which story each article should have, and which it has now.
        new_story_of = {aid: s["id"] for s in stories for aid in s["member_ids"]}
        old_story_of = {a[0]: a[5] for a in articles}
        existing_ids = {row[0] for row in conn.execute("SELECT id FROM stories")}

        # --- 2. Save everything in ONE transaction ---
        with conn.transaction():
            created = updated = 0
            for story in stories:
                changed = conn.execute(UPSERT_SQL, story).fetchone()  # None if unchanged
                if story["id"] not in existing_ids:
                    created += 1
                elif changed is not None:
                    updated += 1

            conn.execute(CLEAR_OLD_SQL, (LOOKBACK_DAYS,))
            ids_changed = 0
            for article_id, story_id in new_story_of.items():
                old = old_story_of[article_id]
                if old != story_id:
                    conn.execute(SET_STORY_SQL, (story_id, article_id))
                    if old is not None:
                        ids_changed += 1  # the article moved to a different story id

            deleted = len(conn.execute(DELETE_EMPTY_SQL).fetchall())

    multi = [s for s in stories if s["article_count"] >= 2]
    print(f"articles assigned:       {len(new_story_of)}")
    print(f"stories total:           {len(stories)}")
    print(f"stories with 2+ articles: {len(multi)}")
    print(f"created / updated / deleted this run: {created} / {updated} / {deleted}")
    print(f"articles whose story id changed:      {ids_changed}")
    print()
    print("5 largest stories:")
    for story in sorted(stories, key=lambda s: (-s["article_count"], s["id"]))[:5]:
        print(f"  {story['article_count']} articles | {story['headline']}")


if __name__ == "__main__":
    main()
