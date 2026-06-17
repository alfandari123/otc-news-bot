import requests
import feedparser
import json
import os


API_KEY = os.getenv("ALPHA_KEY")


with open("watchlist.json", "r") as f:
    watchlist = json.load(f)



message = "📈 OTC Scanner Update\n\n"



for symbol in watchlist:

    price = None
    change = None



    # מקור 1 - Alpha Vantage

    try:

        url = (
            "https://www.alphavantage.co/query?"
            "function=GLOBAL_QUOTE"
            f"&symbol={symbol}"
            f"&apikey={API_KEY}"
        )


        data = requests.get(url).json()

        quote = data.get("Global Quote", {})


        price = quote.get("05. price")
        change = quote.get("10. change percent")


    except:

        pass




    # מקור 2 - Yahoo

    if not price:

        try:

            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            )


            data = requests.get(url).json()


            result = data["chart"]["result"][0]


            meta = result.get("meta", {})


            price = meta.get("regularMarketPrice")



        except:

            pass





    if price:


        message += f"📊 {symbol}\n"
        message += f"💵 Price: {price}\n"


        if change:

            message += f"📈 Change: {change}\n"


        message += "\n"



    else:


        message += f"⚠️ {symbol}\n"
        message += "No price data\n\n"






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
