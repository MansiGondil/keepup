-- One row per story: a group of articles about the same event.
-- A story with one article is fine; most stories have just one.
CREATE TABLE IF NOT EXISTS stories (
    id                        text        PRIMARY KEY,   -- e.g. 'st_20261103_1234'
    headline                  text        NOT NULL,
    representative_article_id bigint,                    -- the article the headline came from
    first_published_at        timestamptz NOT NULL,      -- earliest member article
    last_published_at         timestamptz NOT NULL,      -- latest member article
    article_count             integer     NOT NULL,
    source_count              integer     NOT NULL,      -- distinct outlets
    updated_at                timestamptz NOT NULL DEFAULT now()
);

-- Which story each article belongs to. NULL = no story (yet).
-- If a story is deleted, its articles simply lose their story_id.
ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS story_id text REFERENCES stories(id) ON DELETE SET NULL;

-- Speeds up "all articles of this story" lookups.
CREATE INDEX IF NOT EXISTS articles_story_id_idx ON articles (story_id);
