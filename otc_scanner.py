import os
import json
import re
import requests
import feedparser
import yfinance as yf
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SEEN_FILE = "seen_news.json"
MAX_STORY_AGE_DAYS = 3
MAX_ALERTS_PER_SCAN = 5

GOOD_WORDS = {"10-k":4,"audited":3,"filing":2,"contract":4,"partnership":4,"acquisition":6,"merger":7,"fda":6,"approval":5,"approved":6,"revenue":3,"profit":4,"growth":3,"orders":4,"agreement":4,"expansion":3,"launch":3}
FUTURE_WORDS = {"clinical":3,"trial":3,"phase":3,"pipeline":3,"development":2,"strategic":3,"potential":2,"explore":2,"intends":2,"plans":2,"expected":2}
BAD_WORDS = {"dilution":-5,"reverse split":-5,"bankruptcy":-10,"going concern":-7,"lawsuit":-5,"offering":-4,"toxic":-5}


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("חסרים פרטי חיבור לטלגרם")
        return
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":message,"disable_web_page_preview":"false"}, timeout=15).raise_for_status()


def load_json(file):
    try:
        with open(file,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(file,data):
    with open(file,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=2,ensure_ascii=False)


def get_market_data(symbol):
    try:
        info=yf.Ticker(symbol).fast_info
        return info.get("last_price","לא זמין"),info.get("last_volume","לא זמין")
    except Exception:
        return "לא זמין","לא זמין"


def discover_news(symbol):
    url="https://news.google.com/rss/search?q="+quote(f"{symbol} OTC stock")+"&hl=en-US&gl=US&ceid=US:en"
    try:
        r=requests.get(url,timeout=15,headers={"User-Agent":"OTC-M/3.0"})
        return feedparser.parse(r.content).entries[:15]
    except Exception as exc:
        print(f"שגיאה באיתור חדשות {symbol}: {exc}")
        return []


def parse_published(item):
    if getattr(item,"published_parsed",None):
        try:
            from calendar import timegm
            return datetime.fromtimestamp(timegm(item.published_parsed),tz=timezone.utc)
        except Exception:
            pass
    return None


def get_article_url(item):
    link=item.get("link","")
    if link: return link
    links=item.get("links",[]) or []
    for entry in links:
        if entry.get("href"): return entry["href"]
    return ""


def normalize_title(title):
    text=re.sub(r"[^a-z0-9 ]+"," ",title.lower())
    stop={"the","a","an","and","of","to","for","in","on","with","company","plc","inc"}
    return " ".join(x for x in text.split() if x not in stop)


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
    if score >= 8 and strong:
        return "🟢 חדשות חיוביות מאוד", "אירוע משמעותי שעשוי להשפיע בטווח הקצר"
    if future or score >= 5:
        return "🟡 חדשות עם פוטנציאל עתידי", "אירוע שעשוי להיות חיובי בהמשך, אך עדיין אינו ודאי"
    return "🔵 חדשות למעקב", "מידע מעניין שדורש מעקב נוסף"


def sec_verify(symbol):
    """Find a recent SEC filing for the ticker when SEC has a ticker mapping.
    This is only a corroboration signal; it is NOT proof that the article's claim is true.
    """
    try:
        headers={"User-Agent":"OTC-M verification bot contact: otc-news-bot@example.com","Accept-Encoding":"gzip, deflate"}
        tickers=requests.get("https://www.sec.gov/files/company_tickers.json",headers=headers,timeout=15).json()
        match=None
        for row in tickers.values():
            if str(row.get("ticker","")).upper()==symbol.upper():
                match=row; break
        if not match:
            return False,"לא נמצא רישום SEC לטיקר",""
        cik=str(match["cik_str"]).zfill(10)
        url=f"https://data.sec.gov/submissions/CIK{cik}.json"
        data=requests.get(url,headers=headers,timeout=15).json()
        recent=data.get("filings",{}).get("recent",{})
        forms=recent.get("form",[])
        dates=recent.get("filingDate",[])
        accession=recent.get("accessionNumber",[])
        cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).date().isoformat()
        allowed={"8-K","10-Q","10-K","6-K","20-F","F-1","F-3","S-1","S-3"}
        for i,form in enumerate(forms):
            if form in allowed and i < len(dates) and dates[i] >= cutoff:
                acc=accession[i].replace("-","") if i < len(accession) else ""
                filing_url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/" if acc else "https://www.sec.gov/search-filings"
                return True,f"נמצא דיווח SEC מהשבוע האחרון ({form})",filing_url
        return False,"לא נמצא דיווח SEC רלוונטי מהשבוע האחרון","https://www.sec.gov/search-filings"
    except Exception as exc:
        print(f"שגיאה בבדיקת SEC עבור {symbol}: {exc}")
        return False,"בדיקת SEC לא זמינה כרגע",""


def run_scanner():
    stocks=load_json("otc_stocks.json")
    if not stocks:
        print("לא נמצאה רשימת מניות OTC")
        return

    state=load_json(SEEN_FILE)
    if not isinstance(state,dict): state={}
    today=datetime.now(timezone.utc).date().isoformat()
    today_state=state.setdefault(today,{})
    alerts=[]

    for raw_symbol in stocks[:300]:
        symbol=str(raw_symbol).upper().strip()
        if not symbol: continue

        # First collect only fresh stories, then group near-duplicate coverage of the same event.
        fresh=[]
        for item in discover_news(symbol):
            title=item.get("title","").strip()
            article_url=get_article_url(item)
            published_dt=parse_published(item)
            if not title or not published_dt:
                continue
            age=datetime.now(timezone.utc)-published_dt
            if age < timedelta(0) or age > timedelta(days=MAX_STORY_AGE_DAYS):
                continue
            story_id=(article_url or (title+published_dt.isoformat())).strip().lower()
            ticker_seen=today_state.setdefault(symbol,{})
            if story_id in ticker_seen:
                continue
            ticker_seen[story_id]={"title":title,"published":published_dt.isoformat(),"checked_at":datetime.now(timezone.utc).isoformat()}
            fresh.append((item,title,article_url,published_dt))

        if not fresh:
            continue

        groups=[]
        for item,title,url,published_dt in fresh:
            norm=normalize_title(title)
            placed=False
            for group in groups:
                # Share at least 3 normalized words => likely the same event reported by another outlet.
                common=set(norm.split()) & set(group["norm"].split())
                if len(common)>=3:
                    group["items"].append((item,title,url,published_dt)); placed=True; break
            if not placed:
                groups.append({"norm":norm,"items":[(item,title,url,published_dt)]})

        for group in groups:
            items=group["items"]
            primary=max(items,key=lambda x:x[3])
            _,title,article_url,published_dt=primary
            score=score_news(title)
            if score<5: continue
            status,sec_note,sec_url=sec_verify(symbol)
            label,meaning=classify_news(title,score)
            price,volume=get_market_data(symbol)
            sources=[]
            for _,t,u,p in items[:3]:
                if u: sources.append(f"🔗 {u}")
            source_text="\n".join(sources) if sources else "אין קישור זמין"
            sec_text=f"🛡️ אימות SEC: {sec_note}"
            if sec_url: sec_text+=f"\n🔗 מקור SEC: {sec_url}"
            message=(f"{label}\n\n💲 מניה: {symbol}\n⭐ ציון: {score}/10\n"
                     f"🕒 פורסם: {published_dt.strftime('%d/%m/%Y %H:%M')} UTC\n"
                     f"💰 מחיר: {price}\n📊 מחזור: {volume}\n\n"
                     f"📰 אירוע: {title}\n\n"
                     f"🔗 מקורות הכתבה:\n{source_text}\n\n{sec_text}\n\n"
                     f"💡 משמעות: {meaning}\n\n"
                     f"⚠️ הבוט מציג מידע ומקורות לבדיקה. אימות מקור אינו המלצה להשקעה ואינו מבטיח עלייה או ירידה במניה.")
            alerts.append((score,symbol,message))

    # Keep 14 days of duplicate history. This prevents repeats while allowing a genuinely new story.
    keys=list(state.keys())[-14:]
    state={k:state[k] for k in keys}
    save_json(SEEN_FILE,state)

    # One best alert per ticker per scan, maximum 5 total.
    best={}
    for score,symbol,message in alerts:
        if symbol not in best or score>best[symbol][0]: best[symbol]=(score,message)
    selected=sorted(((s,sym,m) for sym,(s,m) in best.items()),reverse=True)[:MAX_ALERTS_PER_SCAN]
    for _,_,message in selected:
        send_telegram("🇮🇱 OTC M — איתות חדש\n\n"+message+"\n\n🕒 זמן בדיקה: "+datetime.now().strftime("%d/%m/%Y %H:%M"))
    print(f"איתותים חדשים וייחודיים: {len(selected)}")


if __name__=="__main__": run_scanner()
