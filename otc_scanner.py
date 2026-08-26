# OTC-M v8.1 — dependency-safe scanner; do not import yfinance.
import os, json, requests, feedparser, re, base64
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BOT_TOKEN=os.getenv("BOT_TOKEN"); CHAT_ID=os.getenv("CHAT_ID"); SEEN_FILE="seen_news.json"
GITHUB_TOKEN=os.getenv("GITHUB_TOKEN"); GITHUB_REPOSITORY=os.getenv("GITHUB_REPOSITORY","alfandari123/otc-news-bot")
GOOD={"contract":4,"partnership":4,"acquisition":6,"merger":7,"fda":6,"approval":5,"approved":5,"revenue":3,"profit":4,"growth":3,"orders":4,"agreement":4,"expansion":3,"launch":3,"definitive agreement":7,"purchase agreement":6,"milestone":4,"strategic mou":2}
FUTURE={"clinical":3,"trial":3,"phase":3,"pipeline":3,"development":2,"strategic":2,"potential":2,"explore":2,"intends":2,"plans":2,"expected":2}
BAD={"dilution":-5,"reverse split":-5,"bankruptcy":-10,"going concern":-7,"lawsuit":-5,"offering":-4,"toxic":-5}
MAX_AGE_HOURS=72
MIN_ALERT_SCORE=3
MAX_STOCKS_PER_SCAN=250
MAX_NEWS_PER_SYMBOL=5
SOURCE_CHECK_WORKERS=10

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("חסרים פרטי חיבור לטלגרם")
    r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg,"disable_web_page_preview":False},timeout=15)
    r.raise_for_status()

def load_local():
    try:
        with open(SEEN_FILE,encoding="utf-8") as f:
            d=json.load(f); return d if isinstance(d,dict) else {}
    except:return {}

def save_local(d):
    with open(SEEN_FILE,"w",encoding="utf-8") as f:json.dump(d,f,indent=2,ensure_ascii=False)

def load_state():
    d=load_local()
    if d:return d
    if not GITHUB_TOKEN:return {}
    try:
        u=f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{SEEN_FILE}";r=requests.get(u,headers={"Authorization":f"Bearer {GITHUB_TOKEN}","Accept":"application/vnd.github+json"},timeout=10)
        if r.status_code==200:
            remote=json.loads(base64.b64decode(r.json()["content"]).decode());return remote if isinstance(remote,dict) else {}
    except Exception as e:print(f"שגיאה בטעינת היסטוריה: {e}")
    return {}

def persist_state(d):
    save_local(d)
    if not GITHUB_TOKEN:return
    try:
        h={"Authorization":f"Bearer {GITHUB_TOKEN}","Accept":"application/vnd.github+json"};u=f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{SEEN_FILE}";old=requests.get(u,headers=h,timeout=10);payload={"message":"Update persistent OTC alert state","content":base64.b64encode(json.dumps(d,indent=2,ensure_ascii=False).encode()).decode()}
        if old.status_code==200:payload["sha"]=old.json()["sha"]
        requests.put(u,headers=h,json=payload,timeout=10)
    except Exception as e:print(f"שגיאה בשמירת היסטוריה: {e}")

def parse_date_value(v):
    if not v:return None
    for fn in (lambda x:datetime.fromisoformat(str(x).replace("Z","+00:00")),parsedate_to_datetime):
        try:
            d=fn(v);return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
        except:pass
    return None

def extract_source_date(url):
    try:
        r=requests.get(url,timeout=6,headers={"User-Agent":"Mozilla/5.0 (compatible; OTC-M/8.0)"},allow_redirects=True)
        if r.status_code!=200:return None,r.url
        html=r.text[:700000];dates=[]
        patterns=[r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|datePublished|publish(?:ed)?|publication_date|parsely-pub-date)["\'][^>]+content=["\']([^"\']+)',r'"datePublished"\s*:\s*"([^"]+)"',r'<time[^>]+datetime=["\']([^"\']+)["\']']
        for p in patterns:
            for x in re.findall(p,html,re.I):
                d=parse_date_value(x)
                if d:dates.append(d)
        return (min(dates),r.url) if dates else (None,r.url)
    except Exception:return None,url

def event_key(text):
    t=re.sub(r"[^a-z0-9]+"," ",text.lower())
    for w in ["allied energy corporation","afc energy plc","otc","stock","corp","corporation","plc","company","announces","announcement"]:t=t.replace(w," ")
    return " ".join(t.split())

def discover_news(symbol):
    try:
        q=f"{symbol} OTC stock when:3d";u=f'https://news.google.com/rss/search?q={quote(q)}&hl=en-US&gl=US&ceid=US:en'
        r=requests.get(u,timeout=5,headers={"User-Agent":"OTC-M/8.0"});feed=feedparser.parse(r.content)
        return symbol,feed.entries[:MAX_NEWS_PER_SYMBOL]
    except Exception as e:print(f"שגיאת חדשות {symbol}: {e}");return symbol,[]

def score(title,age):
    t=title.lower();s=sum(p for w,p in GOOD.items() if w in t)+sum(p for w,p in FUTURE.items() if w in t)+sum(p for w,p in BAD.items() if w in t)
    if age<=24:s+=2
    elif age>48:s-=1
    return max(0,min(10,s))

def classify(title,s):
    t=title.lower()
    if s>=8 and any(x in t for x in ["merger","acquisition","fda approval","approved","definitive agreement","contract","revenue","profit","orders","purchase agreement"]):return "🟢 חדשות חיוביות מאוד","אירוע משמעותי שעשוי להשפיע בטווח הקצר"
    if any(x in t for x in FUTURE) or s>=5:return "🟡 חדשות עם פוטנציאל עתידי","אירוע שעשוי להיות חיובי בהמשך אך עדיין אינו ודאי"
    return "🔵 חדשות למעקב","מידע שדורש בדיקה ומעקב"

def sec_verify(symbol):
    try:
        h={"User-Agent":"OTC-M verification bot contact: otc-news-bot@example.com"};sub=requests.get("https://www.sec.gov/files/company_tickers.json",headers=h,timeout=6).json();cik=None
        for v in sub.values():
            if str(v.get("ticker","")).upper()==symbol:cik=str(v["cik_str"]).zfill(10);break
        if not cik:return False,"לא נמצא טיקר ב-SEC",""
        url=f"https://data.sec.gov/submissions/CIK{cik}.json";data=requests.get(url,headers=h,timeout=6).json();recent=data.get("filings",{}).get("recent",{});forms=recent.get("form",[]);dates=recent.get("filingDate",[]);cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).date().isoformat();ok=any(i<len(dates) and f in ["8-K","10-Q","10-K","6-K","20-F"] and dates[i]>=cutoff for i,f in enumerate(forms));return ok,"נמצא דיווח רשמי ב-SEC" if ok else "לא נמצא דיווח רשמי עדכני ב-SEC",url
    except:return False,"SEC אינו זמין כרגע",""

def market_data(symbol):
    try:
        url="https://query1.finance.yahoo.com/v8/finance/chart/"+quote(symbol,safe="")+"?range=1d&interval=1m";r=requests.get(url,timeout=5,headers={"User-Agent":"Mozilla/5.0"});data=r.json()["chart"]["result"][0];meta=data.get("meta",{});price=meta.get("regularMarketPrice",meta.get("previousClose","לא זמין"));vol=meta.get("regularMarketVolume","לא זמין");return price,vol
    except:return "לא זמין","לא זמין"

def run_scanner():
    try:
        with open("otc_stocks.json",encoding="utf-8") as f:stocks=json.load(f)
    except Exception as e:print(f"שגיאה ברשימת OTC: {e}");return
    if not stocks:print("לא נמצאה רשימת מניות OTC");return
    state=load_state();today=datetime.now(timezone.utc).date().isoformat();day=state.setdefault(today,{})
    stocks=[str(x).upper().strip() for x in stocks if str(x).strip()][:MAX_STOCKS_PER_SCAN]
    discovery=[]
    with ThreadPoolExecutor(max_workers=25) as pool:
        fs=[pool.submit(discover_news,s) for s in stocks]
        for f in as_completed(fs):
            try:discovery.append(f.result())
            except:pass
    stats={"מניות שנסרקו":len(discovery),"מועמדי RSS":0,"חדשות טריות":0,"ישנות":0,"ללא תאריך מקור":0,"כפולות":0,"ציון נמוך":0,"מועמדים לאיתות":0}
    preliminary=[];now=datetime.now(timezone.utc)
    for symbol,entries in discovery:
        for item in entries:
            stats["מועמדי RSS"]+=1;title=item.get("title","").strip();url=item.get("link","").strip();rss_dt=parse_date_value(item.get("published") or item.get("updated"))
            if not title or not url or not rss_dt:continue
            rss_age=(now-rss_dt).total_seconds()/3600
            if rss_age<0 or rss_age>MAX_AGE_HOURS:stats["ישנות"]+=1;continue
            base=score(title,rss_age)
            if base<MIN_ALERT_SCORE:stats["ציון נמוך"]+=1;continue
            preliminary.append((symbol,title,url))
    qualified=[]
    with ThreadPoolExecutor(max_workers=SOURCE_CHECK_WORKERS) as pool:
        fs=[pool.submit(extract_source_date,url) for _,_,url in preliminary]
        for (symbol,title,url),f in zip(preliminary,fs):
            try:
                dt,final=f.result()
                if not dt:stats["ללא תאריך מקור"]+=1;continue
                age=(now-dt).total_seconds()/3600
                if age<0 or age>MAX_AGE_HOURS:stats["ישנות"]+=1;continue
                stats["חדשות טריות"]+=1;ident=final.lower();ev=event_key(title)
                if ident in day or any(isinstance(v,dict) and (v.get("event")==ev or v.get("source")==final) for v in day.values()):stats["כפולות"]+=1;continue
                s=score(title,age);day[ident]={"event":ev,"title":title,"published":dt.isoformat(),"source":final};qualified.append((s,symbol,title,dt,final));stats["מועמדים לאיתות"]+=1
            except Exception:continue
    persist_state(state);alerts=[]
    for s,symbol,title,dt,url in qualified:
        verified,src,securl=sec_verify(symbol);label,meaning=classify(title,s);price,vol=market_data(symbol)
        msg=(f"{label}\n\n💲 מניה: {symbol}\n⭐ ציון: {s*10}/100\n🕒 פורסם במקור: {dt.strftime('%d/%m/%Y %H:%M')} UTC\n\n📰 אירוע:\n{title}\n\n🔗 קישור למקור:\n{url}\n\n🛡️ מקור רשמי: {src}\n"+(f"🔗 קישור SEC:\n{securl}\n\n" if verified else "\n")+f"💰 מחיר: {price}\n📊 מחזור: {vol}\n\n💡 משמעות: {meaning}\n\n⚠️ מידע לצורכי בדיקה בלבד. אינו המלצה להשקעה ואינו מבטיח עלייה או ירידה.")
        alerts.append((s,symbol,msg))
    best={}
    for s,sym,msg in alerts:
        if sym not in best or s>best[sym][0]:best[sym]=(s,msg)
    selected=sorted(((s,sym,msg) for sym,(s,msg) in best.items()),reverse=True)[:5]
    for _,_,msg in selected:send_telegram("🇮🇱 OTC M — איתות חדש\n\n"+msg+"\n\n🕒 זמן בדיקה: "+datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"))
    print("OTC-M v8.1 — סיכום:",json.dumps(stats,ensure_ascii=False));print(f"איתותים שנשלחו: {len(selected)}")

if __name__=="__main__":run_scanner()
