-- Step 6b: each story's primary category and its 1 to 3 topics
-- (lists in docs/api-contract.md). NULL means "not classified yet".
ALTER TABLE stories
    ADD COLUMN IF NOT EXISTS category text,
    ADD COLUMN IF NOT EXISTS topics   text[];

-- Speeds up "stories with any of these topics" (topics && ARRAY[...]).
CREATE INDEX IF NOT EXISTS stories_topics_idx ON stories USING gin (topics);
