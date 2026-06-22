import feedparser
import yfinance as yf


def get_price(symbol):

    tickers = [
        symbol,
        symbol + ".PK",
        symbol + ".OB"
    ]

    for ticker_symbol in tickers:

        try:

            ticker = yf.Ticker(ticker_symbol)

            data = ticker.history(
                period="5d"
            )

            if not data.empty:

                return data["Close"].iloc[-1]

        except:

            pass

    return None



def get_news(symbol):

    news = feedparser.parse(
        f"https://news.google.com/rss/search?q={symbol}+OTC+stock"
    )

    headlines = []

    for item in news.entries[:3]:

        headlines.append(
            item.title
        )

    return headlines



def check(symbol):

    message = f"📊 OTC Check: {symbol}\n\n"


    price = get_price(symbol)


    if price:

        message += (
            f"💵 Price: {price:.6f}\n\n"
        )

    else:

        message += (
            "⚠️ No price data\n\n"
        )



    message += "📰 News:\n"


    news = get_news(symbol)


    if news:

        for item in news:

            message += f"• {item}\n"

    else:

        message += "No recent news"



    return message



def scan_watchlist(watchlist):

    result = "📈 OTC Scanner Update\n\n"


    for symbol in watchlist:

        result += check(symbol)
        result += "\n\n"


    return result
