-- One row per ingest run, so we can see when runs happened and whether they worked.
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id               bigserial   PRIMARY KEY,
    started_at       timestamptz NOT NULL,
    finished_at      timestamptz,
    ok               boolean,          -- true if the run finished (even if one feed failed)
    duration_seconds numeric,
    items_fetched    integer,
    new_rows         integer,
    skipped          integer,
    sources          jsonb,            -- list of {"feed", "items", "error"}; error is null on success
    error_message    text              -- only set when the whole run crashed
);
