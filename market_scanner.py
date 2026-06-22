import requests
import os
from datetime import datetime


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def get_stock_data(symbol):

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    try:
        response = requests.get(url).json()

        result = response["chart"]["result"][0]

        price = result["meta"]["regularMarketPrice"]

        return price

    except:
        return None



def scan_market():

    stocks = [
        "AITX",
        "SONN",
        "GVSI"
    ]

    message = "📊 OTC Scanner Live\n\n"

    for stock in stocks:

        price = get_stock_data(stock)

        if price:

            message += (
                f"🚨 {stock}\n"
                f"💵 Price: ${price}\n\n"
            )

        else:
            message += f"⚠️ {stock} - no data\n\n"


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


print("Live scanner finished")
