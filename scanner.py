import json
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)

message = "🔎 OTC Scanner Report\n\n"

for symbol in watchlist:
    message += f"Checking: {symbol}\n"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

requests.post(
    url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print("Report sent")
