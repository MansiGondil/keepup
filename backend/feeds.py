"""The list of RSS feeds Keepup reads, plus the request settings.

Each feed has:
  name:    the source name stored in articles.source (e.g. "BBC News")
  section: which part of that source the feed covers (e.g. "world")
  url:     the RSS feed address
  max_items (optional): keep only the newest N items from this feed
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
    {"name": "BBC News", "section": "us_and_canada",
     "url": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"},
    {"name": "BBC News", "section": "business",
     "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
    {"name": "BBC News", "section": "health",
     "url": "https://feeds.bbci.co.uk/news/health/rss.xml"},
    {"name": "BBC News", "section": "science_and_environment",
     "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"},
    {"name": "BBC News", "section": "entertainment_and_arts",
     "url": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"},
    {"name": "NASA", "section": "news-releases",
     "url": "https://www.nasa.gov/news-release/feed/", "max_items": 20},
    {"name": "Federal Reserve", "section": "press-releases",
     "url": "https://www.federalreserve.gov/feeds/press_all.xml", "max_items": 20},
    {"name": "arXiv", "section": "data-ml",
     "url": "https://rss.arxiv.org/rss/cs.LG+stat.ML", "max_items": 25},
    {"name": "arXiv", "section": "tech-ai",
     "url": "https://rss.arxiv.org/rss/cs.AI", "max_items": 25},
]

# Identify ourselves politely to the feed servers.
HEADERS = {"User-Agent": "keepup-portfolio-bot/0.1 (+https://github.com/MansiGondil/keepup)"}
TIMEOUT_SECONDS = 10

# Some servers ask us to wait between requests. arXiv's terms: at most one
# request every 3 seconds, one connection at a time.
MIN_SECONDS_BETWEEN_REQUESTS = {"rss.arxiv.org": 3}
