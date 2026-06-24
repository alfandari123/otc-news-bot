import feedparser

def get_otc_news():

    feed = feedparser.parse(
        "https://www.otcmarkets.com/research/rss/news"
    )

    news = []

    for entry in feed.entries[:10]:

        title = entry.title

        news.append(title)

    return news
