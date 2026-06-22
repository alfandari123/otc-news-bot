import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print("TOKEN:", BOT_TOKEN[:10] if BOT_TOKEN else "MISSING")
print("CHAT:", CHAT_ID)


url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

response = requests.post(
    url,
    data={
        "chat_id": CHAT_ID,
        "text": "🚀 Test from scanner.py"
    }
)

print(response.text)
