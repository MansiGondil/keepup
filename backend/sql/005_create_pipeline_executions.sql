-- One row per run of run_pipeline.py (all its stages together).
-- pipeline_runs (002) still logs each ingest run on its own.
CREATE TABLE IF NOT EXISTS pipeline_executions (
    id            bigserial   PRIMARY KEY,
    started_at    timestamptz NOT NULL,
    finished_at   timestamptz,       -- NULL while running (or if the runner was killed)
    ok            boolean,           -- true if every chosen stage succeeded
    total_seconds numeric,
    stages        jsonb,             -- [{name, status, seconds}, ...]
    funnel        jsonb,             -- {items_fetched, new_articles, stories_in_window, multi_article_stories}
    error_message text               -- failed stage + last error line, max 500 chars
);
