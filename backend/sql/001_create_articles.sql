-- One row per news item we fetch from a feed.
-- We store only metadata and the short feed snippet, never article bodies.
CREATE TABLE IF NOT EXISTS articles (
    id           bigserial   PRIMARY KEY,
    source       text        NOT NULL,              -- e.g. 'BBC News'
    title        text        NOT NULL,
    url          text        NOT NULL UNIQUE,       -- same link = same article
    snippet      text,                              -- short feed description, may be NULL
    published_at timestamptz,                       -- may be NULL if the feed has no date
    fetched_at   timestamptz NOT NULL DEFAULT now()
);

-- Speeds up "newest articles first" queries.
CREATE INDEX IF NOT EXISTS articles_published_at_idx ON articles (published_at);
