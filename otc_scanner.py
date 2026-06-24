import os
import json
import requests
import feedparser
from datetime import datetime


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


GOOD_WORDS = [
    "contract",
    "partnership",
    "acquisition",
    "merger",
    "approval",
    "fda",
    "revenue growth",
    "new orders",
    "agreement",
    "expansion",
    "launch"
]


BAD_WORDS = [
    "price",
    "chart",
    "forecast",
    "history",
    "analysis",
    "dilution",
    "going concern"
]


def send_telegram(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        }
    )


def load_watchlist():

    with open("watchlist.json", "r") as file:
        return json.load(file)



def check_news(symbol):

    url = f"https://news.google.com/rss/search?q={symbol}+stock"

    feed = feedparser.parse(url)

    results = []

    for item in feed.entries[:10]:

        title = item.title.lower()


        if any(word in title for word in GOOD_WORDS):

            if not any(word in title for word in BAD_WORDS):

                results.append(item.title)


    return results



def scanner():

    stocks = load_watchlist()

    alerts = []


    for stock in stocks:

        news = check_news(stock)

        if news:

            alerts.append(
                f"📌 {stock}\n" +
                "\n".join(
                    "• " + n for n in news
                )
            )



    if alerts:

        message = (
            "🚨 OTC QUALITY ALERT\n\n"
            +
            "\n\n".join(alerts)
            +
            f"\n\n🕒 {datetime.now()}"
        )

        send_telegram(message)


    else:

        print("No quality alerts")



scanner()
