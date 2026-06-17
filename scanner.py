import requests
import feedparser
import json
import os


API_KEY = os.getenv("ALPHA_KEY")


with open("watchlist.json","r") as f:
    watchlist = json.load(f)


message = "📈 OTC Scanner Update\n\n"


for symbol in watchlist:

    try:

        url = (
            f"https://www.alphavantage.co/query?"
            f"function=GLOBAL_QUOTE&symbol={symbol}"
            f"&apikey={API_KEY}"
        )


        data = requests.get(url).json()

        quote = data.get("Global Quote", {})


        price = quote.get("05. price")
        change = quote.get("10. change percent")


        if price:

            message += f"🚀 {symbol}\n"
            message += f"💵 Price: {price}\n"
            message += f"📊 Change: {change}\n\n"

        else:

            message += f"⚠️ {symbol}\nNo price\n\n"


    except:

        message += f"⚠️ {symbol}\nError\n\n"



message += "📰 OTC News\n\n"


for symbol in watchlist:

    news = feedparser.parse(
        f"https://news.google.com/rss/search?q={symbol}+OTC+stock"
    )


    for item in news.entries[:2]:

        message += f"• {item.title}\n"



with open("telegram_message.txt","w") as f:
    f.write(message)


print("Scanner finished")
