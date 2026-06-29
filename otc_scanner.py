import os
import json
import requests
import feedparser
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

    "revenue growth": 4,
    "gross margin": 3,
    "profit": 3,

    "new orders": 3,
    "agreement": 3,
    "expansion": 2,
    "launch": 2
}


BAD_WORDS = [

    "dilution",
    "going concern",
    "bankruptcy",
    "lawsuit",
    "reverse split"

]



def send_telegram(message):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )


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
                "User-Agent":
                "Mozilla/5.0"
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



    for item in feed.entries[:15]:


        title = item.title.strip()


        clean_title = (
            title
            .lower()
        )



        if clean_title in seen:

            continue



        score = 0



        for word, points in GOOD_WORDS.items():


            if word in clean_title:

                score += points




        for bad in BAD_WORDS:


            if bad in clean_title:

                score -= 5




        if score >= 4:


            alerts.append(

                {
                    "title": title,
                    "score": score
                }

            )


            seen.append(
                clean_title
            )



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
