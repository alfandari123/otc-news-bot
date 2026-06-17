import json
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)

message = "📈 OTC Watchlist\n\n"

for symbol in watchlist:
    message += f"• {symbol}\n"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

requests.post(
    url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print("Telegram message sent")
