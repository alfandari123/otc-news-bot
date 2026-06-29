import os
import json
import requests
import feedparser
from datetime import datetime


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


GOOD_WORDS = {
    "contract": 3,
    "partnership": 3,
    "acquisition": 4,
    "merger": 5,
    "approval": 4,
    "fda": 5,
    "revenue growth": 3,
    "new orders": 3,
    "agreement": 3,
    "expansion": 2,
    "launch": 2
}


BAD_WORDS = [
    "dilution",
    "going concern",
    "bankruptcy",
    "lawsuit"
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

        json.dump(
            data,
            f,
            indent=2
        )



def load_watchlist():

    try:

        with open(
            "otc_stocks.json",
            "r"
        ) as f:

            return json.load(f)


    except:

        with open(
            "watchlist.json",
            "r"
        ) as f:

            return json.load(f)



def get_price(symbol):

    try:

        url = (
            f"https://query1.finance.yahoo.com/"
            f"v8/finance/chart/{symbol}"
        )


        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=10
        )


        data = response.json()


        price = (
            data["chart"]
            ["result"][0]
            ["meta"]
            ["regularMarketPrice"]
        )


        return price


    except:

        return "N/A"




def check_news(symbol, seen):

    url = (
        f"https://news.google.com/rss/search?"
        f"q={symbol}+stock"
    )


    feed = feedparser.parse(url)


    alerts = []


    for item in feed.entries[:10]:


        title = item.title


        if title in seen:
            continue



        text = title.lower()


        score = 0



        for word, points in GOOD_WORDS.items():

            if word in text:

                score += points



        for bad in BAD_WORDS:

            if bad in text:

                score -= 5



        if score >= 4:


            alerts.append(
                {
                    "title": title,
                    "score": score
                }
            )


            seen.append(title)



    return alerts





def scanner():


    stocks = load_watchlist()


    seen = load_json(
        "seen_news.json"
    )


    results = []



    for stock in stocks:


        news = check_news(
            stock,
            seen
        )



        if news:


            price = get_price(stock)



            for item in news:


                results.append(

                    f"📌 {stock}\n"
                    f"⭐ Score: {item['score']}/10\n"
                    f"💰 Price: {price}\n"
                    f"• {item['title']}"

                )



    save_json(
        "seen_news.json",
        seen
    )



    if results:


        message = (

            "🚨 OTC QUALITY ALERT\n\n"
            +
            "\n\n".join(results)
            +
            f"\n\n🕒 {datetime.now()}"

        )


        send_telegram(
            message
        )


    else:


        print(
            "No high quality alerts"
        )




scanner()
