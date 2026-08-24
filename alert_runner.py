from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import feedparser
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSITIVE = [
    "contract", "agreement", "partnership", "acquisition", "merger", "approval",
    "fda", "patent", "revenue", "profit", "record", "launch", "award", "order",
    "financing", "funding", "strategic", "expansion", "milestone", "clinical"
]
NEGATIVE = [
    "bankruptcy", "default", "delisting", "lawsuit", "fraud", "investigation",
    "offering", "dilution", "reverse split", "going concern", "resignation", "warning"
]


def load_otc_symbols():
    """Load the automatically refreshed OTC symbol list."""
    try:
        with open("otc_stocks.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x).strip().upper() for x in data if str(x).strip()]
    except Exception as exc:
        print(f"Could not load otc_stocks.json: {exc}")
    return []


def news(symbol: str):
    url = (
        "https://news.google.com/rss/search?q="
        + requests.utils.quote(f'"{symbol}" stock OTC')
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    r = requests.get(url, timeout=15, headers={"User-Agent": "OTC-M/1.1"})
    r.raise_for_status()
    return feedparser.parse(r.content).entries[:8]


def score(entries):
    pos = neg = 0
    reasons = []
    for e in entries:
        title = e.get("title", "").lower()
        p = sum(1 for x in POSITIVE if x in title)
        n = sum(1 for x in NEGATIVE if x in title)
        pos += p
        neg += n
        if p:
            reasons.append("חדשה חיובית: " + e.get("title", "")[:180])
        elif n:
            reasons.append("⚠️ חדשות שליליות: " + e.get("title", "")[:180])
    value = max(0, min(100, 50 + pos * 12 - neg * 15))
    return value, reasons


def send(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True},
        timeout=15,
    ).raise_for_status()


def main():
    symbols = load_otc_symbols()
    if not symbols:
        send("🤖 OTC M מחובר ועובד.\n\nלא נמצאה כרגע רשימת OTC. הסריקה תנסה שוב בהרצה הבאה.")
        return

    print(f"Loaded {len(symbols)} OTC symbols")

    # Keep the free GitHub Actions run lightweight while still scanning a broad OTC universe.
    # The list is refreshed by otc_list.py before this runner starts.
    for symbol in symbols[:300]:
        try:
            entries = news(symbol)
            s, reasons = score(entries)
            if s >= 74 or s <= 25:
                emoji = "🚨🟢" if s >= 74 else "🚨🔴"
                text = (
                    f"{emoji} OTC M — התראה\n\n${symbol}\nציון: {s}/100\n\n"
                    + "\n".join("• " + x for x in reasons[:4])
                    + "\n\n⚠️ זה סורק מידע ואינו מבטיח עלייה או ירידה במניה."
                    + f"\n🕒 {datetime.now(timezone.utc).isoformat()}"
                )
                send(text[:3900])
        except Exception as exc:
            print(f"{symbol}: {exc}")


if __name__ == "__main__":
    main()
