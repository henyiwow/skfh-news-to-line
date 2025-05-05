import feedparser

def fetch_news(keyword="新光金控"):
    url = f"https://news.google.com/rss/search?q={keyword}"
    feed = feedparser.parse(url)
    news_list = []
    for entry in feed.entries:
        news_list.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "summary": entry.summary
        })
    return news_list
