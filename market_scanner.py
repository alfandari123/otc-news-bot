import requests
import os
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def get_stock_data(symbol):

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    try:
        response = requests.get(url, timeout=10).json()

        result = response["chart"]["result"][0]

        price = result["meta"].get("regularMarketPrice")

        return price

    except Exception:
        return None


def scan_market():

    stocks = [
        "SONN",
        "AAPL",
        "TSLA"
    ]

    message = "📊 Market Scanner Report\n\n"

    for stock in stocks:

        price = get_stock_data(stock)

        if price is not None:
            message += f"✅ {stock}: ${price}\n"
        else:
            message += f"⚠️ {stock}: no data\n"

    message += f"\n🕒 {datetime.now()}"

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

print("Scanner finished")
