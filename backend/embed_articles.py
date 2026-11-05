"""Step 4b: compute an embedding for every article that doesn't have one yet.

Run from the backend folder:  python embed_articles.py
Safe to re-run: only rows WHERE embedding IS NULL are touched.
"""

import time

from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from db import get_connection

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 64

SELECT_SQL = """
    SELECT id, title, snippet
    FROM articles
    WHERE embedding IS NULL
    ORDER BY id
"""

UPDATE_SQL = """
    UPDATE articles
    SET embedding = %s, embedding_model = %s
    WHERE id = %s
"""

COUNT_MISSING_SQL = "SELECT count(*) FROM articles WHERE embedding IS NULL"


def text_for(title, snippet):
    """The text we embed: title plus snippet, or just the title."""
    if snippet is None:
        return title
    return title + ". " + snippet


def main():
    start = time.monotonic()  # a stopwatch for the duration
    model = SentenceTransformer(MODEL_NAME)

    with get_connection() as conn:
        # Teach psycopg how to send numpy arrays as pgvector "vector" values.
        register_vector(conn)

        rows = conn.execute(SELECT_SQL).fetchall()
        embedded = 0

        # Work through the rows 64 at a time.
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            texts = [text_for(title, snippet) for _id, title, snippet in batch]
            # One 384-number vector per text, scaled to length 1.
            vectors = model.encode(texts, normalize_embeddings=True)

            for (article_id, _title, _snippet), vector in zip(batch, vectors):
                conn.execute(UPDATE_SQL, (vector, MODEL_NAME, article_id))
            conn.commit()  # save this batch, so a crash later keeps it
            embedded += len(batch)

        missing = conn.execute(COUNT_MISSING_SQL).fetchone()[0]

    print(f"rows embedded:           {embedded}")
    print(f"seconds taken:           {time.monotonic() - start:.1f}")
    print(f"still without embedding: {missing}")


if __name__ == "__main__":
    main()
