import yfinance as yf
import feedparser
import json

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)

message = "📈 OTC Scanner Update\n\n"

for symbol in watchlist:

    try:
        ticker = yf.Ticker(symbol)

        data = ticker.history(period="2d")

        if len(data) >= 2:

            price = data["Close"].iloc[-1]
            old_price = data["Close"].iloc[-2]

            change = ((price - old_price) / old_price) * 100

            emoji = "🚀" if change > 0 else "🔻"

            message += f"{emoji} {symbol}\n"
            message += f"💵 Price: {price:.6f}\n"
            message += f"📊 Change: {change:.2f}%\n\n"

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


