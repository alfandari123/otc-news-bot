import requests
import feedparser
import json


with open("watchlist.json", "r") as f:
    watchlist = json.load(f)


message = "📈 OTC Scanner Update\n\n"


for symbol in watchlist:

    try:

        url = f"https://www.otcmarkets.com/stock/{symbol}/quote"

        r = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )


        if r.status_code == 200:

            text = r.text

            message += f"🚀 {symbol}\n"
            message += "💵 OTC data found\n\n"

        else:

            message += f"⚠️ {symbol}\nNo data\n\n"


    except Exception:

        message += f"⚠️ {symbol}\nError\n\n"



message += "📰 OTC News\n\n"


for symbol in watchlist:

    news = feedparser.parse(
        f"https://news.google.com/rss/search?q={symbol}+stock+OTC"
    )


    if news.entries:

        message += f"🔎 {symbol}\n"

        for item in news.entries[:2]:

            message += f"• {item.title}\n"

        message += "\n"



with open("telegram_message.txt", "w") as f:
    f.write(message)


print("Scanner finished")
