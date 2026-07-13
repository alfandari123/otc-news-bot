import os
import json
import requests
import feedparser
import yfinance as yf
from datetime import datetime


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


GOOD_WORDS = {
    "10-k": 4,
    "audited": 3,
    "filing": 2,
    "contract": 3,
    "partnership": 3,
    "acquisition": 5,
    "merger": 5,
    "fda": 5,
    "approval": 4,
    "revenue": 3,
    "profit": 3,
    "growth": 2,
    "orders": 3,
    "agreement": 3,
    "expansion": 2,
    "launch": 2
}


BAD_WORDS = {
    "dilution": -5,
    "reverse split": -5,
    "bankruptcy": -10,
    "going concern": -7,
    "lawsuit": -5,
    "offering": -4,
    "toxic": -5
}


def send_telegram(message):

    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram secrets missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=10
    )



def load_json(file):

    try:
        with open(file, "r") as f:
            return json.load(f)

    except:
        return []



def save_json(file, data):

    with open(file, "w") as f:
        json.dump(
            data,
            f,
            indent=2
        )



def get_market_data(symbol):

    try:

        ticker = yf.Ticker(symbol)

        info = ticker.fast_info

        price = info.get(
            "last_price",
            "N/A"
        )

        volume = info.get(
            "last_volume",
            "N/A"
        )

        return price, volume

    except:

        return "N/A", "N/A"



def analyze_news(symbol, seen):

    url = (
        "https://news.google.com/rss/search?"
        f"q={symbol}+OTC+stock"
    )


    feed = feedparser.parse(url)


    results = []


    for item in feed.entries[:10]:

        title = item.title.strip()

        key = f"{symbol}_{title}".lower()


        if key in seen:
            continue


        text = title.lower()

        score = 0


        for word, points in GOOD_WORDS.items():

            if word in text:
                score += points


        for word, points in BAD_WORDS.items():

            if word in text:
                score += points



        score = max(
            0,
            min(
                score,
                10
            )
        )


        if score >= 5:

            results.append(
                {
                    "symbol": symbol,
                    "title": title,
                    "score": score
                }
            )


            seen.append(key)



    return results




def run_scanner():

    stocks = load_json(
        "otc_stocks.json"
    )


    if not stocks:

        print(
            "No OTC list found"
        )

        return



    seen = load_json(
        "seen_news.json"
    )


    alerts = []


    # הגבלה כדי לא להיחסם
    for symbol in stocks[:300]:

        news = analyze_news(
            symbol,
            seen
        )


        if news:

            price, volume = get_market_data(
                symbol
            )


            for item in news:

                alerts.append(

                    "📌 " + item["symbol"]
                    + "\n"
                    + "⭐ Score: "
                    + str(item["score"])
                    + "/10\n"
                    + "💰 Price: "
                    + str(price)
                    + "\n"
                    + "📊 Volume: "
                    + str(volume)
                    + "\n📰 "
                    + item["title"]

                )



    save_json(
        "seen_news.json",
        seen
    )


    if alerts:

        message = (

            "🚨 OTC QUALITY ALERT\n\n"
            +
            "\n\n".join(alerts[:10])
            +
            "\n\n🕒 "
            +
            str(datetime.now())

        )


        send_telegram(
            message
        )


    else:

        print(
            "No quality alerts"
        )



if __name__ == "__main__":

    run_scanner()
