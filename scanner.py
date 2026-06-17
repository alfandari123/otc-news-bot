import feedparser
import json
import yfinance as yf


with open("watchlist.json", "r") as f:
    watchlist = json.load(f)


message = "📈 OTC Scanner Update\n\n"



for symbol in watchlist:

    price = None


    tickers = [
        symbol,
        symbol + ".PK",
        symbol + ".OB",
        symbol + ".OTC"
    ]


    for ticker_symbol in tickers:

        try:

            ticker = yf.Ticker(ticker_symbol)

            data = ticker.history(
                period="5d"
            )


            if not data.empty:

                price = data["Close"].iloc[-1]

                break


        except:

            pass




    if price:


        message += f"📊 {symbol}\n"
        message += f"💵 Price: {price:.6f}\n\n"


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
