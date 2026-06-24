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



def load_json(file):

    try:

        with open(file, "r") as f:
            return json.load(f)

    except:

        return []



def save_json(file, data):

    with open(file, "w") as f:
        json.dump(data, f, indent=2)



def load_watchlist():

    with open("watchlist.json", "r") as f:
        return json.load(f)



def check_news(symbol, seen):

    url = f"https://news.google.com/rss/search?q={symbol}+stock"

    feed = feedparser.parse(url)

    results = []


    for item in feed.entries[:10]:

        title = item.title


        if title in seen:
            continue


        title_lower = title.lower()


        good = any(
            word in title_lower
            for word in GOOD_WORDS
        )


        bad = any(
            word in title_lower
            for word in BAD_WORDS
        )


        if good and not bad:

            results.append(title)

            seen.append(title)



    return results



def scanner():

    stocks = load_watchlist()

    seen = load_json("seen_news.json")


    alerts = []


    for stock in stocks:

        news = check_news(stock, seen)


        if news:

            alerts.append(
                f"📌 {stock}\n" +
                "\n".join(
                    "• " + n
                    for n in news
                )
            )



    save_json(
        "seen_news.json",
        seen
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

        print("No new quality alerts")



scanner()
