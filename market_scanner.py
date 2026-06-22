import requests
import os
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def get_price(symbol):

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)

        data = r.json()

        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]

        return price

    except Exception as e:
        return "No data"


def scan():

    stocks = [
        "AITX",
        "GVSI",
        "SONN"
    ]

    msg = "📊 OTC Scanner Live\n\n"

    for s in stocks:
        price = get_price(s)
        msg += f"• {s}: {price}\n"

    msg += f"\n🕒 {datetime.now()}"

    return msg


message = scan()


url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

requests.post(
    url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print("Sent to Telegram")
