import requests
import feedparser
import json


with open("watchlist.json", "r") as f:
    watchlist = json.load(f)


message = "📈 OTC Scanner Update\n\n"

alerts = []


for symbol in watchlist:

    try:

        price = None
        change = None


        # ניסיון ראשון - Alpha Vantage
        av_url = (
            f"https://www.alphavantage.co/query?"
            f"function=GLOBAL_QUOTE"
            f"&symbol={symbol}"
            f"&apikey={__import__('os').getenv('ALPHA_KEY')}"
        )


        av_data = requests.get(av_url).json()

        quote = av_data.get("Global Quote", {})


        price = quote.get("05. price")
        change = quote.get("10. change percent")



        # ניסיון שני - Yahoo OTC
        if not price:

            yahoo_url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/"
                f"{symbol}.OB"
            )


            yahoo_data = requests.get(yahoo_url).json()


            result = yahoo_data.get("chart", {}).get("result")


            if result:

                meta = result[0].get("meta", {})

                price = meta.get("regularMarketPrice")



        if price:


            message += f"📊 {symbol}\n"
            message += f"💵 Price: {price}\n"


            if change:

                message += f"📈 Change: {change}\n"


                percent = float(
                    change.replace("%","")
                )


                if percent >= 10:

                    alerts.append(
                        f"🚀 {symbol} {change}"
                    )


                elif percent <= -10:

                    alerts.append(
                        f"⚠️ {symbol} {change}"
                    )


            message += "\n"



        else:


            message += f"⚠️ {symbol}\n"
            message += "No price data\n\n"



    except Exception as e:


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




with open("telegram_message.txt", "w") as f:

    f.write(message)



print("Scanner finished")
