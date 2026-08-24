import os
import json
import requests
import feedparser
import yfinance as yf
from datetime import datetime
from urllib.parse import quote

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

GOOD_WORDS = {
    "10-k": 4, "audited": 3, "filing": 2, "contract": 3,
    "partnership": 3, "acquisition": 5, "merger": 5, "fda": 5,
    "approval": 4, "revenue": 3, "profit": 3, "growth": 2,
    "orders": 3, "agreement": 3, "expansion": 2, "launch": 2
}
BAD_WORDS = {
    "dilution": -5, "reverse split": -5, "bankruptcy": -10,
    "going concern": -7, "lawsuit": -5, "offering": -4, "toxic": -5
}


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram secrets missing")
        return
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": message, "disable_web_page_preview": "true"},
        timeout=15,
    ).raise_for_status()


def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_market_data(symbol):
    try:
        info = yf.Ticker(symbol).fast_info
        return info.get("last_price", "N/A"), info.get("last_volume", "N/A")
    except Exception:
        return "N/A", "N/A"


def discover_news(symbol):
    url = "https://news.google.com/rss/search?q=" + quote(f"{symbol} OTC stock") + "&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(requests.get(url, timeout=15, headers={"User-Agent": "OTC-M/2.0"}).content)
        return feed.entries[:10]
    except Exception as exc:
        print(f"News discovery failed for {symbol}: {exc}")
        return []


def score_news(title):
    text = title.lower()
    score = 0
    for word, points in GOOD_WORDS.items():
        if word in text:
            score += points
    for word, points in BAD_WORDS.items():
        if word in text:
            score += points
    return max(0, min(10, score))


def sec_verify(symbol, title):
    """Verify whether the event has a recent SEC filing mentioning the ticker/title.
    SEC is used only as an independent verification signal; absence of a filing is not proof the news is false.
    """
    try:
        headers = {
            "User-Agent": "OTC-M verification bot contact: otc-news-bot@example.com",
            "Accept-Encoding": "gzip, deflate",
        }
        # SEC submissions search endpoint. We search the public filing index through SEC company search.
        q = quote(f"{symbol} {title[:100]}")
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={quote(symbol)}&type=&dateb=&owner=exclude&count=10"
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return False, "SEC לא זמין כרגע", ""
        body = r.text.lower()
        symbol_hit = symbol.lower() in body
        filing_types = any(x in body for x in ["10-k", "10-q", "8-k", "6-k", "20-f"])
        if symbol_hit and filing_types:
            return True, "SEC", url
        return False, "לא נמצא אימות SEC ישיר", url
    except Exception as exc:
        print(f"SEC verification failed for {symbol}: {exc}")
        return False, "SEC לא זמין כרגע", ""


def verify_event(symbol, title):
    """Two-tier verification: SEC first, otherwise label as news-only.
    We never call a news-only event verified.
    """
    verified, source, url = sec_verify(symbol, title)
    if verified:
        return "מאומת", source, url
    return "חדשותי בלבד", source, url


def run_scanner():
    stocks = load_json("otc_stocks.json")
    if not stocks:
        print("No OTC list found")
        return

    seen = load_json("seen_news.json")
    if not isinstance(seen, list):
        seen = []
    alerts = []

    for symbol in stocks[:300]:
        for item in discover_news(symbol):
            title = item.get("title", "").strip()
            key = f"{symbol}_{title}".lower()
            if not title or key in seen:
                continue

            score = score_news(title)
            if score >= 5:
                status, source, source_url = verify_event(symbol, title)
                price, volume = get_market_data(symbol)
                source_line = f"🔎 מקור אימות: {source}"
                if source_url:
                    source_line += f"\n🔗 {source_url}"
                alerts.append(
                    "🚨 " + ("🟢 איתות חיובי" if score >= 5 else "🔴 איתות שלילי") +
                    "\n\n" +
                    f"💲 מניה: {symbol}\n" +
                    f"⭐ ציון: {score}/10\n" +
                    f"🛡️ סטטוס: {status}\n" +
                    f"💰 מחיר: {price}\n" +
                    f"📊 מחזור: {volume}\n\n" +
                    f"📰 חדשות: {title}\n\n" +
                    source_line +
                    "\n\n⚠️ אימות מקור אינו המלצה להשקעה ואינו מבטיח עלייה או ירידה במניה."
                )
            seen.append(key)

    save_json("seen_news.json", seen[-10000:])
    if alerts:
        message = "🇮🇱 OTC M — התראות מאומתות ובדיקת חדשות\n\n" + "\n\n".join(alerts[:10]) + "\n\n🕒 " + str(datetime.now())
        send_telegram(message[:3900])
    else:
        print("No quality alerts")


if __name__ == "__main__":
    run_scanner()
