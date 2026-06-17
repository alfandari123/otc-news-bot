import requests
import feedparser
import json
import os


API_KEY = os.getenv("ALPHA_KEY")


with open("watchlist.json", "r") as f:
    watchlist = json.load(f)


message = "📈 OTC Scanner Update\n\n"



for symbol in watchlist:

    try:

        price = None
        change = None


        symbols_to_try = [
            symbol,
            symbol + ".OB"
        ]


        for ticker in symbols_to_try:


            url = (
                "https://www.alphavantage.co/query?"
                f"function=GLOBAL_QUOTE"
                f"&symbol={ticker}"
                f"&apikey={API_KEY}"
            )


            data = requests.get(url).json()


            quote = data.get("Global Quote", {})


            if quote.get("05. price"):

                price = quote.get("05. price")
                change = quote.get("10. change percent")
                break




        if price:


            message += f"📊 {symbol}\n"
            message += f"💵 Price: {price}\n"
            message += f"📈 Change: {change}\n\n"



        else:


            message += f"⚠️ {symbol}\n"
            message += "No price data\n\n"




    except Exception:


        message += f"⚠️ {symbol}\n"
        message += "Error\n\n"





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





with open("telegram_message.txt","w") as f:

    f.write(message)



print("Scanner finished")
