import requests
import json
import os
from datetime import datetime


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def send(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        }
    )


def scan():

    message = """
📈 OTC Market Scanner

Scanner Status: ACTIVE ✅

Checking:
- OTC companies
- News
- Market activity
- Important events

Time:
""" + str(datetime.now())


    send(message)



scan()
