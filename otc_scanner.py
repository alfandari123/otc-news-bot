import os, json, requests, feedparser, yfinance as yf, re, base64
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from email.utils import parsedate_to_datetime

BOT_TOKEN=os.getenv("BOT_TOKEN"); CHAT_ID=os.getenv("CHAT_ID"); SEEN_FILE="seen_news.json"
GITHUB_TOKEN=os.getenv("GITHUB_TOKEN"); GITHUB_REPOSITORY=os.getenv("GITHUB_REPOSITORY","alfandari123/otc-news-bot")
GOOD={"10-k":4,"audited":3,"filing":2,"contract":4,"partnership":4,"acquisition":6,"merger":7,"fda":6,"approval":5,"revenue":3,"profit":4,"growth":3,"orders":4,"agreement":4,"expansion":3,"launch":3,"definitive agreement":7}
FUTURE={"clinical":3,"trial":3,"phase":3,"pipeline":3,"development":2,"strategic":3,"potential":2,"explore":2,"intends":2,"plans":2,"expected":2}
BAD={"dilution":-5,"reverse split":-5,"bankruptcy":-10,"going concern":-7,"lawsuit":-5,"offering":-4,"toxic":-5}
MAX_AGE_HOURS=48

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: print("חסרים פרטי חיבור לטלגרם"); return
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg,"disable_web_page_preview":False},timeout=15).raise_for_status()

def load_local():
    try:
        with open(SEEN_FILE,encoding="utf-8") as f:return json.load(f)
    except:return {}

def save_local(d):
    with open(SEEN_FILE,"w",encoding="utf-8") as f:json.dump(d,f,indent=2,ensure_ascii=False)

def load_state():
    d=load_local()
    if d:return d
    if not GITHUB_TOKEN:return {}
    try:
        u=f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{SEEN_FILE}"
        r=requests.get(u,headers={"Authorization":f"Bearer {GITHUB_TOKEN}","Accept":"application/vnd.github+json"},timeout=15)
        if r.status_code==200:
            return json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
    except Exception as e:print(f"שגיאה בטעינת היסטוריה: {e}")
    return {}

def persist_state(d):
    save_local(d)
    if not GITHUB_TOKEN:return
    try:
        h={"Authorization":f"Bearer {GITHUB_TOKEN}","Accept":"application/vnd.github+json"}
        u=f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{SEEN_FILE}"
        old=requests.get(u,headers=h,timeout=15)
        payload={"message":"Update persistent OTC alert state","content":base64.b64encode(json.dumps(d,indent=2,ensure_ascii=False).encode()).decode()}
        if old.status_code==200:payload["sha"]=old.json()["sha"]
        r=requests.put(u,headers=h,json=payload,timeout=15)
        if r.status_code not in (200,201):print(f"שמירת היסטוריה ב-GitHub נכשלה: {r.status_code} {r.text[:200]}")
    except Exception as e:print(f"שגיאה בשמירת היסטוריה: {e}")

def parse_date_value(v):
    if not v:return None
    v=str(v).strip()
    for fn in (lambda x:datetime.fromisoformat(x.replace("Z","+00:00")),parsedate_to_datetime):
        try:
            d=fn(v);return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
        except:pass
    return None

def extract_source_date(url):
    try:
        r=requests.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0 (compatible; OTC-M/6.0)"},allow_redirects=True)
        if r.status_code!=200:return None,r.url
        html=r.text[:1500000]
        patterns=[r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|datePublished|publish(?:ed)?|publication_date)["\'][^>]+content=["\']([^"\']+)',r'"datePublished"\s*:\s*"([^"]+)"',r'<time[^>]+datetime=["\']([^"\']+)["\']']
        dates=[]
        for p in patterns:
            for x in re.findall(p,html,re.I):
                d=parse_date_value(x)
                if d:dates.append(d)
        return (min(dates),r.url) if dates else (None,r.url)
    except Exception as e:print(f"שגיאה בבדיקת תאריך מקור: {e}");return None,url

def canonical(text):return re.sub(r"[^a-z0-9]+"," ",text.lower()).strip()
def event_key(title):
    t=canonical(title)
    for w in ["allied energy corporation","afc energy plc","otc","stock","corp","corporation","plc","company","announces","announcement"]:t=t.replace(w," ")
    return " ".join(t.split())

def discover_news(symbol):
    u="https://news.google.com/rss/search?q="+quote(f'"{symbol}" OTC stock when:2d')+"&hl=en-US&gl=US&ceid=US:en"
    try:return feedparser.parse(requests.get(u,timeout=15,headers={"User-Agent":"OTC-M/6.0"}).content).entries[:15]
    except Exception as e:print(f"שגיאה באיתור חדשות {symbol}: {e}");return []

def score(title,age):
    t=title.lower();s=sum(p for w,p in GOOD.items() if w in t)+sum(p for w,p in FUTURE.items() if w in t)+sum(p for w,p in BAD.items() if w in t)
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
        url=f"https://data.sec.gov/submissions/CIK{cik}.json";data=requests.get(url,headers=h,timeout=15).json();recent=data.get("filings",{}).get("recent",{});forms=recent.get("form",[]);dates=recent.get("filingDate",[]);cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).date().isoformat();ok=any(i<len(dates) and f in ["8-K","10-Q","10-K","6-K","20-F"] and dates[i]>=cutoff for i,f in enumerate(forms));return ok,"נמצא דיווח רשמי ב-SEC" if ok else "לא נמצא דיווח רשמי עדכני ב-SEC",url
    except:return False,"SEC אינו זמין כרגע",""

def run_scanner():
    stocks=[]
    try:
        with open("otc_stocks.json",encoding="utf-8") as f:stocks=json.load(f)
    except:pass
    if not stocks:print("לא נמצאה רשימת מניות OTC");return
    state=load_state();today=datetime.now(timezone.utc).date().isoformat();day=state.setdefault(today,{})
    alerts=[]
    for raw in stocks[:300]:
        symbol=str(raw).upper().strip()
        if not symbol:continue
        for item in discover_news(symbol):
            title=item.get("title","").strip();rss_url=item.get("link","").strip()
            if not title or not rss_url:continue
            source_dt,source_url=extract_source_date(rss_url)
            if not source_dt:continue
            age=(datetime.now(timezone.utc)-source_dt).total_seconds()/3600
            if age<0 or age>MAX_AGE_HOURS:continue
            ticker=day.setdefault(symbol,{});ident=source_url.lower();ev=event_key(title)
            if ident in ticker or any(v.get("event")==ev for v in ticker.values()):continue
            s=score(title,age);ticker[ident]={"event":ev,"title":title,"published":source_dt.isoformat(),"source":source_url}
            if s<5:continue
            verified,src,securl=sec_verify(symbol);label,meaning=classify(title,s)
            try:info=yf.Ticker(symbol).fast_info;price=info.get("last_price","לא זמין");vol=info.get("last_volume","לא זמין")
            except:price=vol="לא זמין"
            msg=(f"{label}\n\n💲 מניה: {symbol}\n⭐ ציון: {s*10}/100\n🕒 פורסם במקור: {source_dt.strftime('%d/%m/%Y %H:%M')} UTC\n\n📰 אירוע:\n{title}\n\n🔗 קישור למקור:\n{source_url}\n\n🛡️ מקור רשמי: {src}\n"+(f"🔗 קישור SEC:\n{securl}\n\n" if verified else "\n")+f"💰 מחיר: {price}\n📊 מחזור: {vol}\n\n💡 משמעות: {meaning}\n\n⚠️ מידע לצורכי בדיקה בלבד. אינו המלצה להשקעה ואינו מבטיח עלייה או ירידה.")
            alerts.append((s,symbol,msg))
    state={k:state[k] for k in list(state)[-14:]};persist_state(state)
    best={}
    for s,sym,msg in alerts:
        if sym not in best or s>best[sym][0]:best[sym]=(s,msg)
    for _,msg in sorted(best.values(),reverse=True)[:5]:send_telegram("🇮🇱 OTC M — איתות חדש\n\n"+msg+"\n\n🕒 זמן בדיקה: "+datetime.now().strftime("%d/%m/%Y %H:%M"))
    print(f"OTC-M v6: איתותים חדשים וייחודיים: {min(5,len(best))}")

if __name__=="__main__":run_scanner()
