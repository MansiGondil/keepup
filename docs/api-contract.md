# Keepup API Contract

All endpoints are read-only `GET` requests that return JSON.
Dates use `YYYY-MM-DD`. Timestamps use ISO 8601 in UTC (e.g. `2026-10-29T07:30:00Z`).

## Categories

Every story has exactly one `category` from this list:

| Category          | Group   |
|-------------------|---------|
| `tech-ai`         | Tech    |
| `data-ml`         | Tech    |
| `devops-security` | Tech    |
| `business`        | General |
| `world`           | General |
| `health`          | General |
| `money`           | General |
| `science`         | General |
| `careers`         | General |
| `sports`          | General |
| `entertainment`   | General |

---

## GET /api/todays-read

Today's briefing: up to 8 story cards. The frontend must handle fewer
(including zero) items.

**Query parameters**

| Name     | Required | Description |
|----------|----------|-------------|
| `topics` | no       | Comma-separated categories, e.g. `tech-ai,health`. Only influences the `for_you` bucket. Unknown values are ignored. |

**Response**

```json
{
  "date": "YYYY-MM-DD",
  "items": [ /* up to 8 story objects */ ]
}
```

**Story object**

| Field            | Type                     | Notes |
|------------------|--------------------------|-------|
| `id`             | string                   | Stable story id. |
| `headline`       | string                   | |
| `summary`        | string                   | Max 60 words. |
| `bucket`         | string                   | `"must_know"` \| `"trending"` \| `"for_you"` |
| `category`       | string                   | One of the categories above. |
| `source_count`   | integer                  | Number of distinct outlets that covered the story. Always `>= sources.length`. |
| `sources`        | list of `{name, url}`    | 1 to 5 items (capped at 5). Links to the original articles. |
| `published_at`   | string (ISO 8601)        | Earliest publication time among the sources. |
| `why_this_story` | string                   | One short sentence. |

**Example** (`GET /api/todays-read?topics=data-ml`, one item shown)

```json
{
  "date": "2026-10-29",
  "items": [
    {
      "id": "st_20261029_001",
      "headline": "Open dataset standard reaches version 2.0",
      "summary": "A community group released version 2.0 of a shared format for describing datasets, adding fields for licensing and data lineage.",
      "bucket": "for_you",
      "category": "data-ml",
      "source_count": 2,
      "sources": [
        { "name": "Example Data Journal", "url": "https://example.com/data/dataset-standard-2" },
        { "name": "Sample Wire", "url": "https://example.com/wire/dataset-format" }
      ],
      "published_at": "2026-10-29T06:15:00Z",
      "why_this_story": "You follow Data & ML, and this changes how datasets are documented."
    }
  ]
}
```

See `data/sample_stories.json` for a full 8-item response.

---

## GET /api/quiz/today

Five questions based on today's read, plus general knowledge.

**Response**

```json
{
  "date": "YYYY-MM-DD",
  "questions": [ /* 5 question objects */ ]
}
```

**Question object**

| Field           | Type             | Notes |
|-----------------|------------------|-------|
| `id`            | string           | |
| `question`      | string           | |
| `options`       | list of string   | Exactly 4. |
| `correct_index` | integer          | 0–3, index into `options`. |
| `explanation`   | string           | Shown after answering. |
| `kind`          | string           | `"from_today"` \| `"general"` |
| `story_id`      | string or null   | Related story id for `from_today`; `null` for `general`. |

**Example** (one question shown)

```json
{
  "date": "2026-10-29",
  "questions": [
    {
      "id": "q_20261029_1",
      "question": "What did version 2.0 of the open dataset standard add?",
      "options": [
        "Video support",
        "Licensing and data lineage fields",
        "A new file compression method",
        "Built-in encryption"
      ],
      "correct_index": 1,
      "explanation": "The release added fields for licensing and data lineage.",
      "kind": "from_today",
      "story_id": "st_20261029_001"
    }
  ]
}
```

---

## GET /api/status

Pipeline health for the most recent run.

**Response**

| Field              | Type      | Notes |
|--------------------|-----------|-------|
| `last_run_at`      | string (ISO 8601) | When the last pipeline run finished. |
| `last_run_ok`      | boolean   | `true` if the run completed without failing. |
| `duration_seconds` | number    | |
| `funnel`           | object    | `{articles_ingested, after_dedupe, stories, summarized}`, all integers. |
| `sources`          | list      | Each `{name, last_success_at, errors_24h}`. `last_success_at` may be `null` if the source never succeeded. |

**Example**

```json
{
  "last_run_at": "2026-10-29T06:00:42Z",
  "last_run_ok": true,
  "duration_seconds": 184.3,
  "funnel": {
    "articles_ingested": 412,
    "after_dedupe": 297,
    "stories": 61,
    "summarized": 61
  },
  "sources": [
    { "name": "Sample Wire", "last_success_at": "2026-10-29T05:58:10Z", "errors_24h": 0 },
    { "name": "Example Data Journal", "last_success_at": "2026-10-28T18:02:55Z", "errors_24h": 3 }
  ]
}
```

---

## Rules

- Summaries never exceed 60 words.
- Every story links to its original sources (`sources` is never empty).
- `why_this_story` may mention the user's topics only when the `topics`
  query parameter was provided.
- The frontend must only rely on fields documented here. New fields may be
  added, but undocumented fields must not be used.
