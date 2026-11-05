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

The `category` is the single primary label shown on a card. Viewers do not
filter on it; they filter on `topics` (below).

## Topics

Every story has 1 to 3 `topics` from this list. Viewers pick the topics
they follow, and the feed follows them.

| Topic           | Covers |
|-----------------|--------|
| `ai`            | AI models, products, research and policy. |
| `data-ml`       | Data engineering, analytics, machine learning. |
| `sre`           | Reliability: outages, incidents and postmortems, observability, on-call, Kubernetes and cloud infrastructure. |
| `security`      | Vulnerabilities, breaches, security tooling. |
| `business`      | Companies, markets, deals. |
| `world`         | International news. |
| `health`        | Health and medicine. |
| `money`         | Personal finance, rates, the economy. |
| `science`       | Science and the environment. |
| `careers`       | Jobs, hiring, the workplace. |
| `sports`        | Sports. |
| `entertainment` | Film, TV, music, the arts. |

---

## GET /api/todays-read

Today's briefing: up to 8 story cards. The frontend must handle fewer
(including zero) items.

**Query parameters**

| Name             | Required | Description |
|------------------|----------|-------------|
| `topics`         | no       | Comma-separated topic tags, e.g. `sre,data-ml,ai`. Unknown tags are ignored. |
| `only_my_topics` | no       | Boolean, default `false`. When `false`, only the `for_you` bucket follows `topics`. When `true`, every item comes from the chosen topics (up to 8, possibly fewer). Ignored when `topics` is omitted. |

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
| `bucket`         | string or null           | `"must_know"` \| `"trending"` \| `"for_you"`. Required (never `null`) in `/api/todays-read`; always `null` in `/api/stories`. |
| `category`       | string                   | One of the categories above. |
| `topics`         | list of string           | 1 to 3 tags from the Topics list. |
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
      "topics": ["data-ml"],
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

## GET /api/stories

A browse feed of recent stories, newest first (by `published_at`), that
match ANY of the given topics. Uses the same story object as
`/api/todays-read`, with `bucket` always `null`.

**Query parameters**

| Name     | Required | Description |
|----------|----------|-------------|
| `topics` | no       | Comma-separated topic tags, e.g. `sre,security`. A story matches if it has at least one of them. Unknown tags are ignored. If `topics` is omitted or empty, or no valid tag remains, all recent stories are returned. |
| `limit`  | no       | Max items to return. Default `20`, max `50`. |
| `cursor` | no       | Opaque string. Omit it for the first page; to get the next page, pass the `next_cursor` from the previous response. |

Pagination uses a cursor instead of a timestamp because many stories can
share the same `published_at` (for example arXiv papers), so a timestamp
alone cannot mark a page boundary.

**Response**

```json
{
  "items": [ /* up to `limit` story objects, newest first */ ],
  "next_cursor": "<string>" | null
}
```

`next_cursor` is `null` on the last page.

**Example** (`GET /api/stories?topics=sre&limit=1`)

```json
{
  "items": [
    {
      "id": "st_20261029_007",
      "headline": "Researchers disclose flaw in common container image tool",
      "summary": "Security researchers disclosed a flaw in a common container image build tool that could let a malicious image read files on the build host. A patched version is available, and maintainers recommend upgrading CI runners first.",
      "bucket": null,
      "category": "devops-security",
      "topics": ["sre", "security"],
      "source_count": 3,
      "sources": [
        { "name": "Example Security Bulletin", "url": "https://example.com/security/container-tool-flaw" },
        { "name": "Example Ops Weekly", "url": "https://example.com/ops/patch-your-build-runners" },
        { "name": "Placeholder Tech News", "url": "https://example.com/tech/container-vulnerability" }
      ],
      "published_at": "2026-10-29T01:05:00Z",
      "why_this_story": "Anyone running container builds in CI should patch soon."
    }
  ],
  "next_cursor": "Q3Vyc29yRXhhbXBsZQ"
}
```

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
- `bucket` is always set in `/api/todays-read` and always `null` in
  `/api/stories`.
- `why_this_story` may mention the user's topics only when the `topics`
  query parameter was provided.
- The frontend must only rely on fields documented here. New fields may be
  added, but undocumented fields must not be used.
