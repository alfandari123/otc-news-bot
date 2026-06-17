import requests
import feedparser
import json


with open("watchlist.json", "r") as f:
    watchlist = json.load(f)


message = "📈 OTC Scanner Update\n\n"


for symbol in watchlist:

    try:

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

        data = requests.get(url).json()

        result = data["chart"]["result"][0]

        price = result["meta"]["regularMarketPrice"]

        message += f"🚀 {symbol}\n"
        message += f"💵 Price: {price}\n\n"


    except Exception as e:

        message += f"⚠️ {symbol}\nNo price data\n\n"



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

