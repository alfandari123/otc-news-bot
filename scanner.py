import yfinance as yf
import feedparser
import json

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)

message = "📈 OTC Scanner Update\n\n"

for symbol in watchlist:
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")

        if not data.empty:
            price = data["Close"].iloc[-1]
            message += f"🔹 {symbol}\n"
            message += f"💵 Price: {price:.6f}\n\n"
        else:
            message += f"🔹 {symbol}\nNo data\n\n"

    except Exception as e:
        message += f"🔹 {symbol}\nError\n\n"


message += "📰 Latest OTC News\n\n"

news = feedparser.parse(
    "https://news.google.com/rss/search?q=OTC+stock"
)

for item in news.entries[:5]:
    message += f"• {item.title}\n"

with open("telegram_message.txt", "w") as f:
    f.write(message)

print("Scanner finished")
