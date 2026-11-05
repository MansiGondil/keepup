"""The list of RSS feeds Keepup reads, plus the request settings.

Each feed has:
  name:    the source name stored in articles.source (e.g. "BBC News")
  section: which part of that source the feed covers (e.g. "world")
  url:     the RSS feed address
"""

FEEDS = [
    {"name": "BBC News", "section": "top",
     "url": "https://feeds.bbci.co.uk/news/rss.xml"},
    {"name": "BBC News", "section": "technology",
     "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    {"name": "Hacker News", "section": "front-page",
     "url": "https://news.ycombinator.com/rss"},
    {"name": "BBC News", "section": "world",
     "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "BBC News", "section": "business",
     "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
    {"name": "BBC News", "section": "health",
     "url": "https://feeds.bbci.co.uk/news/health/rss.xml"},
    {"name": "BBC News", "section": "science_and_environment",
     "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"},
    {"name": "BBC News", "section": "entertainment_and_arts",
     "url": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"},
]

# Identify ourselves politely to the feed servers.
HEADERS = {"User-Agent": "keepup-portfolio-bot/0.1 (+https://github.com/MansiGondil/keepup)"}
TIMEOUT_SECONDS = 10
