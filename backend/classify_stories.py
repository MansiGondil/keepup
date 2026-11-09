"""Step 6b: classify every story and save its category and topics.

Run from the backend folder:  python classify_stories.py
Uses the keyword rules in classify.py. Safe to re-run: a story's row is
only updated when its labels change, and everything is saved in one
transaction (all or nothing).
"""

import sys
from collections import Counter

from classify import classify
from db import get_connection

# Print non-English letters correctly in the Windows console.
sys.stdout.reconfigure(encoding="utf-8")

# Our arXiv feeds only cover AI and machine learning, so their papers may
# only get these topics ("study" in an abstract does not make it science).
ALLOWED_TOPICS_OF_SOURCE = {"arXiv": {"ai", "data-ml"}}

# Used when no keyword matches.
FALLBACK_TOPIC_OF_SOURCE = {"arXiv": "ai"}
DEFAULT_FALLBACK_TOPIC = "world"

# One row per story: its headline, the representative article's source and
# snippet, and its current labels.
STORIES_SQL = """
    SELECT s.id, s.headline, a.source, a.snippet, s.category, s.topics
    FROM stories s
    LEFT JOIN articles a ON a.id = s.representative_article_id
    ORDER BY s.id
"""

UPDATE_SQL = """
    UPDATE stories SET category = %s, topics = %s, updated_at = now()
    WHERE id = %s
"""


def main():
    with get_connection() as conn:
        rows = conn.execute(STORIES_SQL).fetchall()

        changed = 0
        categories = Counter()
        with conn.transaction():
            for story_id, headline, source, snippet, old_category, old_topics in rows:
                fallback = FALLBACK_TOPIC_OF_SOURCE.get(source, DEFAULT_FALLBACK_TOPIC)
                allowed = ALLOWED_TOPICS_OF_SOURCE.get(source)
                category, topics = classify(headline, snippet or "", fallback, allowed)
                categories[category] += 1
                if (category, topics) != (old_category, old_topics):
                    conn.execute(UPDATE_SQL, (category, topics, story_id))
                    changed += 1

    print(f"stories classified: {len(rows)}")
    print(f"labels changed:     {changed}")
    print()
    print("stories per category:")
    for category, count in categories.most_common():
        print(f"  {category:<16} {count}")


if __name__ == "__main__":
    main()
