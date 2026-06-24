import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime


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


def get_otc_data():

    url = "https://www.otcmarkets.com/research/stock-screener"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        text = soup.get_text(" ")

        return text


    except Exception as e:

        return str(e)



def scan_market():

    data = get_otc_data()


    keywords = [
        "contract",
        "agreement",
        "acquisition",
        "merger",
        "approval",
        "partnership",
        "revenue",
        "launch"
    ]


    found = []


    for word in keywords:

        if word.lower() in data.lower():

            found.append(word)



    if found:

        message = (
            "🚨 OTC ALERT\n\n"
            "Positive signals found:\n\n"
        )


        for item in found:

            message += f"✅ {item}\n"


        message += f"\n🕒 {datetime.now()}"


        send_telegram(message)


    else:


        send_telegram(
            "🔎 OTC Scanner checked\n\n"
            "No important events found.\n"
            "Scanner is active ✅\n\n"
            f"🕒 {datetime.now()}"
        )



scan_market()
