import os
import requests
import feedparser
import json
from datetime import datetime


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


NEWS_URL = "https://feeds.feedburner.com/otcmarkets/news"


def send_telegram(text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text
        }
    )


def get_news():

    feed = feedparser.parse(NEWS_URL)

    good_words = [
        "agreement",
        "contract",
        "acquisition",
        "merger",
        "approval",
        "partnership",
        "revenue",
        "launch"
    ]

    alerts = []

    for item in feed.entries[:20]:

        title = item.title

        if any(word.lower() in title.lower() for word in good_words):

            alerts.append(title)


    return alerts



news = get_news()


if news:

    message = "🚨 OTC NEWS ALERT\n\n"

    for n in news:
        message += f"• {n}\n\n"

    message += f"🕒 {datetime.now()}"

    send_telegram(message)

else:

    print("No important news found")
