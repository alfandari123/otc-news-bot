import os, json, requests, feedparser, yfinance as yf, re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from email.utils import parsedate_to_datetime

BOT_TOKEN=os.getenv("BOT_TOKEN"); CHAT_ID=os.getenv("CHAT_ID"); SEEN_FILE="seen_news.json"
GOOD={"10-k":4,"audited":3,"filing":2,"contract":4,"partnership":4,"acquisition":6,"merger":7,"fda":6,"approval":5,"revenue":3,"profit":4,"growth":3,"orders":4,"agreement":4,"expansion":3,"launch":3}
FUTURE={"clinical":3,"trial":3,"phase":3,"pipeline":3,"development":2,"strategic":3,"potential":2,"explore":2,"intends":2,"plans":2,"expected":2}
BAD={"dilution":-5,"reverse split":-5,"bankruptcy":-10,"going concern":-7,"lawsuit":-5,"offering":-4,"toxic":-5}
MAX_AGE_HOURS=72


def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: print("חסרים פרטי חיבור לטלגרם"); return
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg,"disable_web_page_preview":"false"},timeout=15).raise_for_status()

def load_json(f):
    try:
        with open(f,encoding="utf-8") as x:return json.load(x)
    except:return {}

def save_json(f,d):
    with open(f,"w",encoding="utf-8") as x:json.dump(d,x,indent=2,ensure_ascii=False)

def news_date(item):
    for key in ("published","updated"):
        raw=item.get(key) or item.get(f"{key}_parsed")
        try:
            if key.endswith("_parsed"): return datetime(*raw[:6],tzinfo=timezone.utc)
            return parsedate_to_datetime(raw).astimezone(timezone.utc)
        except: pass
    return None

def article_url(item): return item.get("link","")

def canonical(text):
    return re.sub(r"[^a-z0-9]+"," ",text.lower()).strip()

def event_key(title):
    t=canonical(title)
    for w in ["allied energy corporation","otc","stock","corp","corporation"]: t=t.replace(w," ")
    return " ".join(t.split())

def discover_news(symbol):
    url="https://news.google.com/rss/search?q="+quote(f'"{symbol}" OTC stock when:3d')+"&hl=en-US&gl=US&ceid=US:en"
    try:
        r=requests.get(url,timeout=15,headers={"User-Agent":"OTC-M/3.0"}); return feedparser.parse(r.content).entries[:15]
    except Exception as e: print(f"שגיאה באיתור חדשות {symbol}: {e}"); return []

def score(title,age):
    t=title.lower(); s=0
    for w,p in GOOD.items():
        if w in t:s+=p
    for w,p in FUTURE.items():
        if w in t:s+=p
    for w,p in BAD.items():
        if w in t:s+=p
    if age is not None:
        if age<=24:s+=2
        elif age>48:s-=2
    return max(0,min(10,s))

def classify(title,s):
    t=title.lower()
    if s>=8 and any(x in t for x in ["merger","acquisition","fda approval","approved","definitive agreement","contract","revenue","profit","orders"]): return "🟢 חדשות חיוביות מאוד","אירוע משמעותי שעשוי להשפיע בטווח הקצר"
    if any(x in t for x in FUTURE) or s>=5:return "🟡 חדשות עם פוטנציאל עתידי","אירוע שעשוי להיות חיובי בהמשך אך עדיין אינו ודאי"
    return "🔵 חדשות למעקב","מידע שדורש בדיקה ומעקב"

def sec_verify(symbol):
    try:
        h={"User-Agent":"OTC-M verification bot contact: otc-news-bot@example.com"}
        sub=requests.get(f"https://www.sec.gov/files/company_tickers.json",headers=h,timeout=15).json()
        cik=None
        for v in sub.values():
            if str(v.get("ticker","")).upper()==symbol: cik=str(v["cik_str"]).zfill(10);break
        if not cik:return False,"לא נמצא טיקר ב-SEC",""
        url=f"https://data.sec.gov/submissions/CIK{cik}.json"
        data=requests.get(url,headers=h,timeout=15).json(); forms=data.get("filings",{}).get("recent",{}).get("form",[])
        dates=data.get("filings",{}).get("recent",{}).get("filingDate",[])
        recent=any(f in ["8-K","10-Q","10-K","6-K","20-F"] and i<len(dates) and dates[i]>= (datetime.now(timezone.utc)-timedelta(days=7)).date().isoformat() for i,f in enumerate(forms))
        return recent,"SEC" if recent else "לא נמצא דיווח SEC עדכני",url
    except Exception:return False,"SEC אינו זמין כרגע",""

def run_scanner():
    stocks=load_json("otc_stocks.json")
    if not stocks:print("לא נמצאה רשימת מניות OTC");return
    state=load_json(SEEN_FILE)
    if not isinstance(state,dict):state={}
    today=datetime.now(timezone.utc).date().isoformat(); day=state.setdefault(today,{})
    alerts=[]
    for raw in stocks[:300]:
        symbol=str(raw).upper().strip()
        for item in discover_news(symbol):
            title=item.get("title","").strip(); url=article_url(item); dt=news_date(item)
            if not title or not dt:continue
            age=(datetime.now(timezone.utc)-dt).total_seconds()/3600
            if age<0 or age>MAX_AGE_HOURS:continue
            ident=(url or event_key(title)).lower(); ticker=day.setdefault(symbol,{})
            ev=event_key(title)
            # Same event is suppressed for the whole day even when another site republishes it.
            if ident in ticker or ev in {v.get("event","") for v in ticker.values()}:continue
            s=score(title,age); ticker[ident]={"event":ev,"title":title,"published":dt.isoformat()}
            if s<5:continue
            verified,src,securl=sec_verify(symbol); label,meaning=classify(title,s)
            price,vol="לא זמין","לא זמין"
            try:
                info=yf.Ticker(symbol).fast_info;price=info.get("last_price","לא זמין");vol=info.get("last_volume","לא זמין")
            except:pass
            msg=(f"{label}\n\n💲 מניה: {symbol}\n⭐ ציון: {s*10}/100\n🕒 פורסם: {dt.strftime('%d/%m/%Y %H:%M')} UTC\n\n📰 אירוע:\n{title}\n\n🔗 קישור לכתבה:\n{url}\n\n🛡️ אימות מקור: {src}\n"+(f"🔗 מקור SEC:\n{securl}\n\n" if securl else "\n")+f"💰 מחיר: {price}\n📊 מחזור: {vol}\n\n💡 משמעות: {meaning}\n\n⚠️ מידע לצורכי בדיקה בלבד. אינו המלצה להשקעה ואינו מבטיח עלייה או ירידה.")
            alerts.append((s,symbol,msg))
    state={k:state[k] for k in list(state)[-14:]};save_json(SEEN_FILE,state)
    best={}
    for s,sym,msg in alerts:
        if sym not in best or s>best[sym][0]:best[sym]=(s,msg)
    for _,msg in sorted(best.values(),reverse=True)[:5]:send_telegram("🇮🇱 OTC M — איתות חדש\n\n"+msg+"\n\n🕒 זמן בדיקה: "+datetime.now().strftime("%d/%m/%Y %H:%M"))
    print(f"איתותים חדשים וייחודיים: {min(5,len(best))}")

if __name__=="__main__":run_scanner()
