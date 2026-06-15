import json
import feedparser

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)

with open("seen_news.json", "r") as f:
    seen_news = json.load(f)

for symbol in watchlist:

    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"

    feed = feedparser.parse(url)

    if not feed.entries:
        print(f"No news found for {symbol}")
        continue

    latest = feed.entries[0]

    title = latest.title
    link = latest.link

    print(f"Symbol: {symbol}")
    print(f"Title: {title}")
    print(f"Link: {link}")
