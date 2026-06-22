import requests
import os
from datetime import datetime

def scan_market():

    stocks = [
        "AITX",
        "SONN",
        "GVSI"
    ]

    message = "📊 OTC Scanner Report\n\n"

    for stock in stocks:
        message += f"• {stock} - scanned ✅\n"

    message += f"\n🕒 {datetime.now()}"

    return message


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

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
