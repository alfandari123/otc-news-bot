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

    with open("watchlist.json", "r") as file:
        return json.load(file)



def check_news(symbol):

    url = f"https://news.google.com/rss/search?q={symbol}+stock"

    feed = feedparser.parse(url)

    news_list = []

    for item in feed.entries[:5]:

        news_list.append(item.title)

    return news_list



def scanner():

    stocks = load_watchlist()

    message = "🚨 OTC Scanner Report\n\n"

    found = False


    for stock in stocks:

        news = check_news(stock)


        if news:

            found = True

            message += f"📌 {stock}\n"

            for n in news:

                message += f"• {n}\n"

            message += "\n"



    if found:

        message += f"🕒 {datetime.now()}"

        send_telegram(message)


    else:

        send_telegram(
            "🔎 OTC Scanner Check\n\n"
            "No new important news found.\n"
            "Scanner is running ✅\n\n"
            f"🕒 {datetime.now()}"
        )



scanner()
