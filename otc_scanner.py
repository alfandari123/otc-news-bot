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


def get_otc_news():

    url = "https://www.otcmarkets.com/research/stock-screener"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        r = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        text = soup.get_text(" ")

        return text[:500]


    except Exception as e:

        return f"Error: {e}"



def scanner():

    data = get_otc_news()


    positive_words = [
        "contract",
        "agreement",
        "acquisition",
        "merger",
        "approval",
        "partnership",
        "revenue"
    ]


    found = []


    for word in positive_words:

        if word.lower() in data.lower():

            found.append(word)



    if found:


        message = (
            "🚨 OTC ALERT\n\n"
            "Positive signals detected:\n\n"
            + "\n".join(found)
            +
            f"\n\n🕒 {datetime.now()}"
        )


        send_telegram(message)


    else:

        print("No important OTC events")



scanner()
