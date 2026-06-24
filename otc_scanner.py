import os
import json
import requests
import feedparser
from datetime import datetime


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


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

    with open("watchlist.json", "r") as f:
        return json.load(f)



def check_news(symbol):

    url = f"https://news.google.com/rss/search?q={symbol}+stock"

    feed = feedparser.parse(url)

    positive = [
        "contract",
        "agreement",
        "merger",
        "acquisition",
        "partnership",
        "approval",
        "revenue",
        "launch"
    ]

    alerts = []

    for item in feed.entries[:10]:

        title = item.title

        for word in positive:

            if word.lower() in title.lower():

                alerts.append(title)

    return alerts



def scanner():

    stocks = load_watchlist()

    message = "🚨 OTC Scanner Report\n\n"

    found = False


    for stock in stocks:

        news = check_news(stock)


        if news:

            found = True

            message += f"📌 {stock}\n\n"

            for n in news[:3]:

                message += f"• {n}\n"

            message += "\n"



    if found:

        message += f"🕒 {datetime.now()}"

        send_telegram(message)


    else:

        print("No important OTC news found")



scanner()
