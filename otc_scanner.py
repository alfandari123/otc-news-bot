import os, json, requests, feedparser, yfinance as yf, re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from email.utils import parsedate_to_datetime

BOT_TOKEN=os.getenv("BOT_TOKEN"); CHAT_ID=os.getenv("CHAT_ID"); SEEN_FILE="seen_news.json"
GOOD={"10-k":4,"audited":3,"filing":2,"contract":4,"partnership":4,"acquisition":6,"merger":7,"fda":6,"approval":5,"revenue":3,"profit":4,"growth":3,"orders":4,"agreement":4,"expansion":3,"launch":3}
FUTURE={"clinical":3,"trial":3,"phase":3,"pipeline":3,"development":2,"strategic":3,"potential":2,"explore":2,"intends":2,"plans":2,"expected":2}
BAD={"dilution":-5,"reverse split":-5,"bankruptcy":-10,"going concern":-7,"lawsuit":-5,"offering":-4,"toxic":-5}
MAX_AGE_HOURS=48

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: print("חסרים פרטי חיבור לטלגרם"); return
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg,"disable_web_page_preview":"false"},timeout=15).raise_for_status()

def load_json(f):
    try:
        with open(f,encoding="utf-8") as x:return json.load(x)
    except:return {}

def save_json(f,d):
    with open(f,"w",encoding="utf-8") as x:json.dump(d,x,indent=2,ensure_ascii=False)

def parse_date_value(value):
    if not value:return None
    value=str(value).strip()
    try:return datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(timezone.utc)
    except:pass
    try:return parsedate_to_datetime(value).astimezone(timezone.utc)
    except:return None

def extract_source_date(url):
    """Use the original publisher page, not Google News RSS, to determine publication date."""
    try:
        r=requests.get(url,timeout=12,headers={"User-Agent":"Mozilla/5.0 (compatible; OTC-M/5.1)"},allow_redirects=True)
        if r.status_code!=200:return None,r.url
        html=r.text[:1000000]
        patterns=[r'"datePublished"\s*:\s*"([^"]+)"',r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)',r'<meta[^>]+name=["\']publish(?:ed|date)["\'][^>]+content=["\']([^"\']+)',r'<time[^>]+datetime=["\']([^"\']+)["\']']
        dates=[]
        for p in patterns:
            for m in re.findall(p,html,re.I):
                d=parse_date_value(m)
                if d:dates.append(d)
        if dates:return min(dates),r.url
        return None,r.url
    except Exception as e:
        print(f"שגיאה בבדיקת תאריך מקור: {e}");return None,url

def canonical(text):return re.sub(r"[^a-z0-9]+"," ",text.lower()).strip()

def event_key(title):
    t=canonical(title)
    for w in ["allied energy corporation","afc energy plc","otc","stock","corp","corporation","plc","company","announces","announcement"]:t=t.replace(w," ")
    t=re.sub(r"\b\d{1,4}\b"," ",t)
    return " ".join(t.split())

def discover_news(symbol):
    url="https://news.google.com/rss/search?q="+quote(f'"{symbol}" OTC stock when:2d')+"&hl=en-US&gl=US&ceid=US:en"
    try:
        r=requests.get(url,timeout=15,headers={"User-Agent":"OTC-M/5.1"});return feedparser.parse(r.content).entries[:15]
    except Exception as e:print(f"שגיאה באיתור חדשות {symbol}: {e}");return []

def score(title,age):
    t=title.lower();s=0
    for w,p in GOOD.items():
        if w in t:s+=p
    for w,p in FUTURE.items():
        if w in t:s+=p
    for w,p in BAD.items():
        if w in t:s+=p
    if age<=24:s+=2
    elif age>36:s-=2
    return max(0,min(10,s))

def classify(title,s):
    t=title.lower()
    if s>=8 and any(x in t for x in ["merger","acquisition","fda approval","approved","definitive agreement","contract","revenue","profit","orders"]):return "🟢 חדשות חיוביות מאוד","אירוע משמעותי שעשוי להשפיע בטווח הקצר"
    if any(x in t for x in FUTURE) or s>=5:return "🟡 חדשות עם פוטנציאל עתידי","אירוע שעשוי להיות חיובי בהמשך אך עדיין אינו ודאי"
    return "🔵 חדשות למעקב","מידע שדורש בדיקה ומעקב"

def sec_verify(symbol):
    try:
        h={"User-Agent":"OTC-M verification bot contact: otc-news-bot@example.com"};sub=requests.get("https://www.sec.gov/files/company_tickers.json",headers=h,timeout=15).json();cik=None
        for v in sub.values():
            if str(v.get("ticker","")).upper()==symbol:cik=str(v["cik_str"]).zfill(10);break
        if not cik:return False,"לא נמצא טיקר ב-SEC",""
        url=f"https://data.sec.gov/submissions/CIK{cik}.json";data=requests.get(url,headers=h,timeout=15).json();recent=data.get("filings",{}).get("recent",{});forms=recent.get("form",[]);dates=recent.get("filingDate",[]);cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).date().isoformat()
        ok=any(i<len(dates) and f in ["8-K","10-Q","10-K","6-K","20-F"] and dates[i]>=cutoff for i,f in enumerate(forms))
        return ok,"נמצא דיווח רשמי ב-SEC" if ok else "לא נמצא דיווח רשמי עדכני ב-SEC",url
    except:return False,"SEC אינו זמין כרגע",""

def run_scanner():
    stocks=load_json("otc_stocks.json")
    if not stocks:print("לא נמצאה רשימת מניות OTC");return
    state=load_json(SEEN_FILE)
    if not isinstance(state,dict):state={}
    today=datetime.now(timezone.utc).date().isoformat();day=state.setdefault(today,{})
    alerts=[]
    for raw in stocks[:300]:
        symbol=str(raw).upper().strip()
        if not symbol:continue
        for item in discover_news(symbol):
            title=item.get("title","").strip();rss_url=item.get("link","").strip()
            if not title or not rss_url:continue
            # Google News is discovery only. The original publisher page MUST supply a real publication date.
            source_dt,source_url=extract_source_date(rss_url)
            if not source_dt:continue
            age=(datetime.now(timezone.utc)-source_dt).total_seconds()/3600
            if age<0 or age>MAX_AGE_HOURS:continue
            ticker=day.setdefault(symbol,{})
            ident=source_url.lower();ev=event_key(title)
            if ident in ticker or any(v.get("event")==ev for v in ticker.values()):continue
            s=score(title,age);ticker[ident]={"event":ev,"title":title,"published":source_dt.isoformat(),"source":source_url}
            if s<5:continue
            verified,src,securl=sec_verify(symbol);label,meaning=classify(title,s)
            try:info=yf.Ticker(symbol).fast_info;price=info.get("last_price","לא זמין");vol=info.get("last_volume","לא זמין")
            except:price=vol="לא זמין"
            msg=(f"{label}\n\n💲 מניה: {symbol}\n⭐ ציון: {s*10}/100\n🕒 פורסם במקור: {source_dt.strftime('%d/%m/%Y %H:%M')} UTC\n\n📰 אירוע:\n{title}\n\n🔗 קישור למקור:\n{source_url}\n\n🛡️ מקור רשמי: {src}\n"+(f"🔗 קישור SEC:\n{securl}\n\n" if verified else "\n")+f"💰 מחיר: {price}\n📊 מחזור: {vol}\n\n💡 משמעות: {meaning}\n\n⚠️ מידע לצורכי בדיקה בלבד. אינו המלצה להשקעה ואינו מבטיח עלייה או ירידה.")
            alerts.append((s,symbol,msg))
    state={k:state[k] for k in list(state)[-14:]};save_json(SEEN_FILE,state)
    best={}
    for s,sym,msg in alerts:
        if sym not in best or s>best[sym][0]:best[sym]=(s,msg)
    for _,msg in sorted(best.values(),reverse=True)[:5]:send_telegram("🇮🇱 OTC M — איתות חדש\n\n"+msg+"\n\n🕒 זמן בדיקה: "+datetime.now().strftime("%d/%m/%Y %H:%M"))
    print(f"איתותים חדשים וייחודיים: {min(5,len(best))}")

if __name__=="__main__":run_scanner()
