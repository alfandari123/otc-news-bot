import os
import json
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def send_telegram(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        }
    )


watchlist = []

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)


message = "📈 OTC Watchlist\n\n"

for symbol in watchlist:
    message += f"• {symbol}\n"

send_telegram(message)

print("Watchlist sent")
