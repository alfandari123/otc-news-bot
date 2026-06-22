import os
import yfinance as yf
import requests
from datetime import datetime


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def get_stock(symbol):

    try:
        stock = yf.Ticker(symbol)

        price = stock.fast_info["last_price"]

        return price

    except Exception:
        return None



def scan_market():

    stocks = [
        "AITX",
        "GVSI",
        "SONN"
    ]

    message = "📈 OTC Scanner Live\n\n"

    for stock in stocks:

        price = get_stock(stock)

        if price:
            message += f"🚨 {stock}\n💵 Price: {price}\n\n"
        else:
            message += f"⚠️ {stock} no data\n\n"


    message += f"🕒 {datetime.now()}"

    return message



message = scan_market()


url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


requests.post(
    url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)


print("Scanner sent")
