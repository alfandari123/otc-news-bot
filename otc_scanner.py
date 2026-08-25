import os
import json
import requests
import feedparser
import yfinance as yf
from datetime import datetime, timezone
from urllib.parse import quote

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SEEN_FILE = "seen_news.json"

GOOD_WORDS = {"10-k":4,"audited":3,"filing":2,"contract":4,"partnership":4,"acquisition":6,"merger":7,"fda":6,"approval":5,"revenue":3,"profit":4,"growth":3,"orders":4,"agreement":4,"expansion":3,"launch":3}
FUTURE_WORDS = {"clinical":3,"trial":3,"phase":3,"pipeline":3,"development":2,"strategic":3,"potential":2,"explore":2,"intends":2,"plans":2,"expected":2}
BAD_WORDS = {"dilution":-5,"reverse split":-5,"bankruptcy":-10,"going concern":-7,"lawsuit":-5,"offering":-4,"toxic":-5}


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("חסרים פרטי חיבור לטלגרם")
        return
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":message,"disable_web_page_preview":"false"}, timeout=15).raise_for_status()


def load_json(file):
    try:
        with open(file,"r",encoding="utf-8") as f: return json.load(f)
    except Exception: return {}


def save_json(file,data):
    with open(file,"w",encoding="utf-8") as f: json.dump(data,f,indent=2,ensure_ascii=False)


def get_market_data(symbol):
    try:
        info=yf.Ticker(symbol).fast_info
        return info.get("last_price","לא זמין"),info.get("last_volume","לא זמין")
    except Exception: return "לא זמין","לא זמין"


def discover_news(symbol):
    url="https://news.google.com/rss/search?q="+quote(f"{symbol} OTC stock")+"&hl=en-US&gl=US&ceid=US:en"
    try:
        r=requests.get(url,timeout=15,headers={"User-Agent":"OTC-M/2.2"})
        return feedparser.parse(r.content).entries[:10]
    except Exception as exc:
        print(f"שגיאה באיתור חדשות {symbol}: {exc}")
        return []


def score_news(title):
    text=title.lower(); score=0
    for word,points in GOOD_WORDS.items():
        if word in text: score+=points
    for word,points in FUTURE_WORDS.items():
        if word in text: score+=points
    for word,points in BAD_WORDS.items():
        if word in text: score+=points
    return max(0,min(10,score))


def classify_news(title,score):
    text=title.lower()
    strong=any(x in text for x in ["merger","acquisition","fda approval","approved","contract","partnership","agreement","revenue","profit","orders"])
    future=any(x in text for x in FUTURE_WORDS)
    if score >= 8 and strong: return "🟢 חדשות חיוביות מאוד", "חדשות משמעותיות עם פוטנציאל השפעה מיידי"
    if future or score >= 5: return "🟡 חדשות עם פוטנציאל עתידי", "אירוע שעשוי להיות חיובי בהמשך אך עדיין אינו ודאי"
    return "🔵 חדשות למעקב", "מידע מעניין שדורש מעקב"


def sec_verify(symbol):
    try:
        headers={"User-Agent":"OTC-M verification bot contact: otc-news-bot@example.com","Accept-Encoding":"gzip, deflate"}
        url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={quote(symbol)}&type=&dateb=&owner=exclude&count=10"
        r=requests.get(url,headers=headers,timeout=15)
        if r.status_code != 200: return False,"SEC אינו זמין כרגע",url
        body=r.text.lower()
        if symbol.lower() in body and any(x in body for x in ["10-k","10-q","8-k","6-k","20-f"]):
            return True,"SEC",url
        return False,"לא נמצא אימות SEC ישיר",url
    except Exception:
        return False,"SEC אינו זמין כרגע",""


def get_article_url(item):
    return item.get("link","") or item.get("links",[{}])[0].get("href","") if item.get("links") else item.get("link","")


def run_scanner():
    stocks=load_json("otc_stocks.json")
    if not stocks:
        print("לא נמצאה רשימת מניות OTC")
        return

    # Store per-ticker events by calendar day. Same ticker can alert again today only for a genuinely new story.
    state=load_json(SEEN_FILE)
    if not isinstance(state,dict): state={}
    today=datetime.now(timezone.utc).date().isoformat()
    today_state=state.setdefault(today,{})
    alerts=[]

    for raw_symbol in stocks[:300]:
        symbol=str(raw_symbol).upper().strip()
        if not symbol: continue
        for item in discover_news(symbol):
            title=item.get("title","").strip()
            article_url=get_article_url(item)
            published=item.get("published","")
            if not title: continue
            # Prefer URL as the unique story identity; fallback to normalized title.
            story_id=(article_url or title).strip().lower()
            ticker_seen=today_state.setdefault(symbol,{})
            if story_id in ticker_seen:
                continue

            score=score_news(title)
            # Mark every story as seen immediately, even if it does not qualify, preventing repeated scans.
            ticker_seen[story_id]={"title":title,"published":published,"checked_at":datetime.now(timezone.utc).isoformat()}
            if score < 5:
                continue

            status,source,sec_url=sec_verify(symbol)
            label,meaning=classify_news(title,score)
            price,volume=get_market_data(symbol)
            article_line=f"🔗 קישור לכתבה: {article_url}" if article_url else "🔗 קישור לכתבה: לא סופק על ידי המקור"
            verification_line=f"🛡️ אימות: {status}"
            if sec_url and source == "SEC": verification_line += f"\n🔗 מקור SEC: {sec_url}"

            message=(f"{label}\n\n💲 מניה: {symbol}\n⭐ ציון: {score}/10\n"
                     f"🛡️ סטטוס מקור: {status}\n💰 מחיר: {price}\n📊 מחזור: {volume}\n\n"
                     f"📰 כותרת: {title}\n\n{article_line}\n{verification_line}\n\n"
                     f"💡 משמעות: {meaning}\n\n⚠️ אימות מקור אינו המלצה להשקעה ואינו מבטיח עלייה או ירידה במניה.")
            alerts.append((score,symbol,message))

    # Keep only a compact recent history; the day keys are retained for same-day duplicate protection.
    keys=list(state.keys())[-14:]
    state={k:state[k] for k in keys}
    save_json(SEEN_FILE,state)

    # One Telegram message per ticker, maximum 5 per scan, highest score first.
    best={}
    for score,symbol,message in alerts:
        if symbol not in best or score > best[symbol][0]: best[symbol]=(score,message)
    selected=sorted(((s,sym,m) for sym,(s,m) in best.items()),reverse=True)[:5]
    for _,_,message in selected:
        send_telegram("🇮🇱 OTC M — איתות חדש\n\n"+message+"\n\n🕒 זמן בדיקה: "+datetime.now().strftime("%d/%m/%Y %H:%M"))
    print(f"איתותים חדשים וייחודיים: {len(selected)}")


if __name__=="__main__": run_scanner()
