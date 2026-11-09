"""Step 6a: give a story its topics and category with keyword rules.

Plain deterministic code (no LLM). Topics and categories come from
docs/api-contract.md.

Run from the backend folder:  python classify.py
It classifies the stories in data/sample_stories.json and compares the
result with their hand-made labels. Nothing is saved to the database yet.
"""

import json
import re
import sys
from pathlib import Path

# Print non-English letters correctly in the Windows console.
sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent
SAMPLE_FILE = BACKEND_DIR.parent / "data" / "sample_stories.json"

# Topic -> words or phrases that point to it. Matched as whole words,
# ignoring case. A word ending in "*" also matches longer forms
# ("vulnerab*" matches "vulnerability" and "vulnerabilities").
TOPIC_KEYWORDS = {
    "ai": ["ai", "artificial intelligence", "llm*", "language model*", "chatbot*",
           "openai", "anthropic", "gemini", "chatgpt", "claude", "copilot",
           "neural", "generative", "code assistant", "agent*", "transformer*"],
    "data-ml": ["data*", "dataset*", "dataframe*", "machine learning", "analytics",
                "sql", "database*", "pandas", "spark", "warehouse", "pipeline*",
                "regression", "classifier*", "training", "benchmark*", "statistic*"],
    "sre": ["outage*", "downtime", "incident*", "postmortem*", "kubernetes",
            "cloud", "aws", "azure", "observability", "on-call", "uptime",
            "restores service", "container*", "devops", "server*", "ci"],
    "security": ["security", "vulnerab*", "flaw*", "breach*", "hack*", "malware",
                 "ransomware", "exploit*", "patch*", "phishing", "cyber*", "cve"],
    "business": ["compan*", "market*", "shares", "deal*", "merger*", "acquisition*",
                 "startup*", "revenue", "profit*", "ceo", "investor*", "firm*"],
    "world": ["war", "election*", "government*", "president", "minister*",
              "united nations", "un", "border*", "troops", "ceasefire", "country",
              "lawmakers", "parliament", "sanction*"],
    "health": ["health*", "hospital*", "doctor*", "patient*", "disease*", "cancer",
               "vaccine*", "nhs", "medic*", "sleep", "mental health", "drug*"],
    "money": ["interest rate*", "inflation", "central bank", "mortgage*", "tax*",
              "pension*", "savings", "economy", "economic", "prices", "wages"],
    "science": ["scien*", "study", "space", "nasa", "climate",
                "species", "physics", "planet*", "environment*", "fossil*"],
    "careers": ["job*", "hiring", "layoff*", "workers", "workplace", "employ*",
                "career*", "salary", "salaries", "remote work"],
    "sports": ["football", "soccer", "cricket", "tennis", "match", "league",
               "cup", "olympic*", "marathon", "championship*", "nba", "nfl",
               "world cup", "goal*", "coach"],
    "entertainment": ["film*", "movie*", "tv", "series", "music", "album*", "singer",
                      "actor*", "actress", "oscar*", "festival", "netflix", "concert*"],
}

# The category shown on the card follows the story's strongest topic.
CATEGORY_OF_TOPIC = {
    "ai": "tech-ai",
    "data-ml": "data-ml",
    "sre": "devops-security",
    "security": "devops-security",
}  # every other topic has a category with the same name

HEADLINE_WEIGHT = 2   # a match in the headline counts double
MAX_TOPICS = 3
FALLBACK_TOPIC = "world"  # used when no keyword matches at all


def keyword_pattern(keyword):
    """Turn one keyword into a whole-word regular expression."""
    if keyword.endswith("*"):
        return r"\b" + re.escape(keyword[:-1]) + r"\w*"
    return r"\b" + re.escape(keyword) + r"\b"


# Build each topic's regex once, at start-up.
TOPIC_PATTERNS = {
    topic: re.compile("|".join(keyword_pattern(k) for k in words), re.IGNORECASE)
    for topic, words in TOPIC_KEYWORDS.items()
}


def topic_scores(headline, text=""):
    """How strongly each topic matches. Topics with no match are left out."""
    scores = {}
    for topic, pattern in TOPIC_PATTERNS.items():
        score = HEADLINE_WEIGHT * len(pattern.findall(headline)) + len(pattern.findall(text))
        if score > 0:
            scores[topic] = score
    return scores


def classify(headline, text="", fallback_topic=FALLBACK_TOPIC):
    """Return (category, topics) for one story.

    headline: the story headline
    text:     extra text such as the feed snippet (optional)
    fallback_topic: used when nothing matches
    """
    scores = topic_scores(headline, text)
    if not scores:
        topics = [fallback_topic]
    else:
        # Strongest first; ties go to the topic listed first in TOPIC_KEYWORDS.
        order = list(TOPIC_KEYWORDS)
        ranked = sorted(scores, key=lambda t: (-scores[t], order.index(t)))
        best = scores[ranked[0]]
        # Keep extra topics only if they are at least half as strong as the best.
        topics = [t for t in ranked if scores[t] * 2 >= best][:MAX_TOPICS]
    category = CATEGORY_OF_TOPIC.get(topics[0], topics[0])
    return category, topics


def main():
    items = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))["items"]
    category_hits = topic_hits = 0
    for item in items:
        category, topics = classify(item["headline"], item["summary"])
        category_ok = category == item["category"]
        topic_ok = topics[0] in item["topics"]  # our top topic is one of theirs
        category_hits += category_ok
        topic_hits += topic_ok
        mark = "ok  " if category_ok and topic_ok else "MISS"
        print(f"{mark} {item['headline']}")
        print(f"     got:      {category:<16} {topics}")
        print(f"     expected: {item['category']:<16} {item['topics']}")
    print()
    print(f"category correct:  {category_hits}/{len(items)}")
    print(f"top topic correct: {topic_hits}/{len(items)}")


if __name__ == "__main__":
    main()
