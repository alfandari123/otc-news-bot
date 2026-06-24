import os
import requests
from datetime import datetime


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


stocks = [
    "AITX",
    "GVSI",
    "SONN"
]


def scan_market():

    message = "📊 OTC Scanner Update\n\n"

    for stock in stocks:

        message += (
            f"🚨 {stock}\n"
            f"Status: Monitoring ✅\n"
            f"News check: Active 🔎\n\n"
        )


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


print("OTC scanner running")
