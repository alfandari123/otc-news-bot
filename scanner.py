import requests
import feedparser
import json
import os


API_KEY = os.getenv("ALPHA_KEY")


with open("watchlist.json", "r") as f:
    watchlist = json.load(f)


message = "📈 OTC Scanner Update\n\n"

alerts = []


for symbol in watchlist:

    try:

        url = (
            f"https://www.alphavantage.co/query?"
            f"function=GLOBAL_QUOTE"
            f"&symbol={symbol}"
            f"&apikey={API_KEY}"
        )


        data = requests.get(url).json()

        quote = data.get("Global Quote", {})


        price = quote.get("05. price")
        change = quote.get("10. change percent")


        if price and change:


            percent = float(
                change.replace("%","")
            )


            if percent >= 10:

                emoji = "🚀"
                alerts.append(
                    f"🚀 {symbol} +{change}"
                )


            elif percent <= -10:

                emoji = "⚠️"
                alerts.append(
                    f"⚠️ {symbol} {change}"
                )


            else:

                emoji = "📊"



            message += f"{emoji} {symbol}\n"
            message += f"💵 Price: {price}\n"
            message += f"📊 Change: {change}\n\n"


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




if alerts:


    message += "\n🚨 ALERTS\n\n"


    for alert in alerts:

        message += alert + "\n"




with open("telegram_message.txt","w") as f:

    f.write(message)



print("Scanner finished")
