"""Step 7a: write a short summary (max 60 words) for one story with the LLM.

Run from the backend folder:  python summarize.py
It summarizes the 3 biggest recent stories and prints the results.
Nothing is saved to the database yet.
"""

import re
import sys

from db import get_connection
from llm import LLMError, generate

# Print non-English letters correctly in the Windows console.
sys.stdout.reconfigure(encoding="utf-8")

MAX_WORDS = 60          # rule from docs/api-contract.md
MAX_SNIPPETS = 5        # articles of one story we show the LLM
MAX_SNIPPET_CHARS = 600
DEMO_STORIES = 3

PROMPT = """You write summaries for a daily news briefing.

Summarize the news story below in 2 or 3 plain sentences, at most {max_words} words.
Rules:
- Use ONLY the facts in the headline and snippets. Do not add anything else.
- Neutral tone. No hype, no opinions, no questions, no emojis.
- Do not start with "This story" or "The article".
- Reply with the summary text only.

Headline: {headline}

Snippets from the outlets that covered it:
{snippets}
"""

# Biggest stories of the last 2 days, with up to MAX_SNIPPETS member snippets.
DEMO_SQL = """
    SELECT s.id, s.headline,
           array_remove((array_agg(a.source || ': ' || a.snippet ORDER BY a.published_at))
                        [1:%(max_snippets)s], NULL)
    FROM stories s
    JOIN articles a ON a.story_id = s.id
    WHERE s.last_published_at >= now() - interval '2 days'
    GROUP BY s.id, s.headline, s.article_count
    ORDER BY s.article_count DESC, s.id
    LIMIT %(limit)s
"""


def clean_snippet(text):
    """Feed snippets can contain HTML tags; keep plain text, cut long ones."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_SNIPPET_CHARS]


def limit_words(text, max_words=MAX_WORDS):
    """Make sure the summary has at most max_words words.

    If it is too long, keep the complete sentences that fit; if not even the
    first sentence fits, cut it and end with "...".
    """
    text = re.sub(r"\s+", " ", text).strip().strip('"')
    if len(text.split()) <= max_words:
        return text
    kept = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if len((" ".join(kept + [sentence])).split()) > max_words:
            break
        kept.append(sentence)
    if kept:
        return " ".join(kept)
    return " ".join(text.split()[:max_words - 1]) + "..."


def summarize(headline, snippets):
    """Return a summary of at most MAX_WORDS words. Raises LLMError on failure."""
    cleaned = [clean_snippet(s) for s in snippets if s and s.strip()][:MAX_SNIPPETS]
    snippet_text = "\n".join(f"- {s}" for s in cleaned) or "- (no snippets)"
    prompt = PROMPT.format(max_words=MAX_WORDS, headline=headline, snippets=snippet_text)
    return limit_words(generate(prompt))


def main():
    with get_connection() as conn:
        stories = conn.execute(DEMO_SQL, {"max_snippets": MAX_SNIPPETS,
                                          "limit": DEMO_STORIES}).fetchall()
    if not stories:
        print("no stories from the last 2 days; run the pipeline first")
        return

    for story_id, headline, snippets in stories:
        print(f"{story_id} | {headline}")
        try:
            summary = summarize(headline, snippets)
        except LLMError as error:
            print(f"  FAILED: {error}")
            if error.rate_limited:
                print("  (free-tier quota used up; try again later)")
                break
            continue
        print(f"  ({len(summary.split())} words) {summary}")
        print()


if __name__ == "__main__":
    main()
