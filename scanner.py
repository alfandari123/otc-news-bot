import requests
import feedparser
import json
import re


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

        html = r.text


        price = re.search(
            r'"last":"?([0-9.]+)',
            html
        )


        if price:

            current_price = price.group(1)

            message += f"🚀 {symbol}\n"
            message += f"💵 Price: {current_price}\n\n"

        else:

            message += f"⚠️ {symbol}\nPrice unavailable\n\n"


    except Exception as e:

        message += f"⚠️ {symbol}\nError\n\n"



message += "📰 OTC News\n\n"


for symbol in watchlist:

    news = feedparser.parse(
        f"https://news.google.com/rss/search?q={symbol}+OTC+stock"
    )


    if news.entries:

        message += f"🔎 {symbol}\n"

        for item in news.entries[:2]:

            message += f"• {item.title}\n"

        message += "\n"



with open("telegram_message.txt", "w") as f:
    f.write(message)


print("Scanner finished")
