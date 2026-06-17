import requests
import feedparser
import json


with open("watchlist.json", "r") as f:
    watchlist = json.load(f)


message = "📈 OTC Scanner Update\n\n"



for symbol in watchlist:

    price = None


    try:


        url = (
            f"https://www.otcmarkets.com/stock/{symbol}/quote"
        )


        r = requests.get(
            url,
            headers={
                "User-Agent":"Mozilla/5.0"
            }
        )


        text = r.text



        words = [
            "lastPrice",
            "last",
            "price"
        ]


        for word in words:

            if word in text:

                start = text.find(word)

                part = text[start:start+100]


                numbers = [
                    x for x in part.replace('"',' ').replace(':',' ').split()
                    if x.replace('.','').isdigit()
                ]


                if numbers:

                    price = numbers[0]
                    break





    except:

        pass




    if price:


        message += f"📊 {symbol}\n"
        message += f"💵 Price: {price}\n\n"


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
