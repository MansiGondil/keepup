-- Turn on pgvector, which adds the "vector" column type.
CREATE EXTENSION IF NOT EXISTS vector;

-- One embedding per article: 384 numbers from all-MiniLM-L6-v2.
-- NULL means "not embedded yet". embedding_model records which model made it.
ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS embedding       vector(384),
    ADD COLUMN IF NOT EXISTS embedding_model text;
