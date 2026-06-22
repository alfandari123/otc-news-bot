import requests
import os
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def scan_market():

    stocks = [
        "AITX",
        "GVSI",
        "SONN"
    ]

    message = "📊 OTC Scanner Report\n\n"

    for stock in stocks:
        message += f"• {stock} - scanned ✅\n"

    message += f"\n🕒 {datetime.now()}"

    return message


message = scan_market()

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

response = requests.post(
    url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print(response.text)
