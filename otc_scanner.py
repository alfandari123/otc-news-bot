import os,json,requests,feedparser,re,base64
from datetime import datetime,timezone,timedelta
from urllib.parse import quote
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor,as_completed

BOT_TOKEN=os.getenv("BOT_TOKEN"); CHAT_ID=os.getenv("CHAT_ID")
SEEN_FILE="seen_news.json"; GITHUB_TOKEN=os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY=os.getenv("GITHUB_REPOSITORY","alfandari123/otc-news-bot")
MAX_AGE_HOURS=72; MIN_ALERT_SCORE=3; MAX_STOCKS_PER_SCAN=250; MAX_NEWS_PER_SYMBOL=5
GOOD={"contract":4,"partnership":4,"acquisition":6,"merger":7,"fda":6,"approval":5,"approved":5,"revenue":3,"profit":4,"growth":3,"orders":4,"agreement":4,"expansion":3,"launch":3,"definitive agreement":7,"purchase agreement":6,"milestone":4,"strategic mou":2}
FUTURE={"clinical":3,"trial":3,"phase":3,"pipeline":3,"development":2,"strategic":2,"potential":2,"explore":2,"intends":2,"plans":2,"expected":2}
BAD={"dilution":-5,"reverse split":-5,"bankruptcy":-10,"going concern":-7,"lawsuit":-5,"offering":-4,"toxic":-5}

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: raise RuntimeError("חסרים פרטי חיבור לטלגרם")
    r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":msg,"disable_web_page_preview":False},timeout=15)
    r.raise_for_status()

def parse_date(v):
    if not v:return None
    for fn in (lambda x:datetime.fromisoformat(str(x).replace("Z","+00:00")),parsedate_to_datetime):
        try:
            d=fn(v); return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
        except: pass
    return None

def load_state():
    try:
        with open(SEEN_FILE,encoding="utf-8") as f:
            d=json.load(f); return d if isinstance(d,dict) else {}
    except: pass
    if GITHUB_TOKEN:
        try:
            u=f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{SEEN_FILE}"
            r=requests.get(u,headers={"Authorization":f"Bearer {GITHUB_TOKEN}"},timeout=10)
            if r.status_code==200:
                d=json.loads(base64.b64decode(r.json()["content"]).decode()); return d if isinstance(d,dict) else {}
        except Exception as e: print(f"שגיאה בטעינת היסטוריה: {e}")
    return {}

def persist_state(d):
    with open(SEEN_FILE,"w",encoding="utf-8") as f: json.dump(d,f,indent=2,ensure_ascii=False)
    if not GITHUB_TOKEN:return
    try:
        h={"Authorization":f"Bearer {GITHUB_TOKEN}","Accept":"application/vnd.github+json"}
        u=f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{SEEN_FILE}"
        old=requests.get(u,headers=h,timeout=10); p={"message":"Update persistent OTC alert state","content":base64.b64encode(json.dumps(d,indent=2,ensure_ascii=False).encode()).decode()}
        if old.status_code==200:p["sha"]=old.json()["sha"]
        requests.put(u,headers=h,json=p,timeout=10)
    except Exception as e: print(f"שגיאה בשמירת היסטוריה: {e}")

def source_date(url):
    try:
        r=requests.get(url,timeout=8,headers={"User-Agent":"Mozilla/5.0 (compatible; OTC-M/8.3)"},allow_redirects=True)
        if r.status_code!=200:return None,r.url
        html=r.text[:1000000]; found=[]
        patterns=[r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|datePublished|datecreated|publish(?:ed)?|publication_date|parsely-pub-date)["\'][^>]+content=["\']([^"\']+)',r'"datePublished"\s*:\s*"([^"]+)"',r'<time[^>]+datetime=["\']([^"\']+)["\']']
        for p in patterns:
            for x in re.findall(p,html,re.I):
                d=parse_date(x)
                if d:found.append(d)
        return (min(found),r.url) if found else (None,r.url)
    except:return None,url

def event_key(title):
    t=re.sub(r"[^a-z0-9]+"," ",title.lower())
    for w in ("otc","stock","corp","corporation","plc","company","announces","announcement"):t=t.replace(w," ")
    return " ".join(t.split())

def discover(symbol):
    try:
        u=f'https://news.google.com/rss/search?q={quote(symbol+" OTC stock when:3d")}&hl=en-US&gl=US&ceid=US:en'
        r=requests.get(u,timeout=8,headers={"User-Agent":"OTC-M/8.3"})
        return symbol,feedparser.parse(r.content).entries[:MAX_NEWS_PER_SYMBOL]
    except Exception as e: print(f"שגיאת חדשות {symbol}: {e}"); return symbol,[]

def score(title,age):
    t=title.lower(); s=sum(p for w,p in GOOD.items() if w in t)+sum(p for w,p in FUTURE.items() if w in t)+sum(p for w,p in BAD.items() if w in t)
    if age<=24:s+=2
    elif age>48:s-=1
    return max(0,min(10,s))

def classify(title,s):
    t=title.lower()
    if s>=8 and any(x in t for x in ("merger","acquisition","fda approval","approved","definitive agreement","contract","revenue","profit","orders","purchase agreement")):return "🟢 חדשות חיוביות מאוד","אירוע משמעותי שעשוי להשפיע בטווח הקצר"
    if any(x in t for x in FUTURE) or s>=5:return "🟡 חדשות עם פוטנציאל עתידי","אירוע שעשוי להיות חיובי בהמשך אך עדיין אינו ודאי"
    return "🔵 חדשות למעקב","מידע שדורש בדיקה ומעקב"

def run_scanner():
    try:
        with open("otc_stocks.json",encoding="utf-8") as f:stocks=json.load(f)
    except Exception as e: print(f"שגיאה ברשימת OTC: {e}"); return
    stocks=[str(x).upper().strip() for x in stocks if str(x).strip()][:MAX_STOCKS_PER_SCAN]
    state=load_state(); today=datetime.now(timezone.utc).date().isoformat(); day=state.setdefault(today,{})
    now=datetime.now(timezone.utc); candidates=[]; stats={"מניות שנסרקו":0,"כתבות RSS":0,"עברו תאריך RSS":0,"נפסלו ישנות":0,"ללא תאריך מקור":0,"כפילויות":0,"ציון נמוך":0}
    with ThreadPoolExecutor(max_workers=25) as pool:
        fs=[pool.submit(discover,s) for s in stocks]
        for f in as_completed(fs):
            try:sym,items=f.result();stats["מניות שנסרקו"]+=1
            except:continue
            for item in items:
                stats["כתבות RSS"]+=1; title=item.get("title","").strip(); url=item.get("link","").strip(); rss=parse_date(item.get("published") or item.get("updated"))
                if not title or not url or not rss:continue
                age=(now-rss).total_seconds()/3600
                if age<0 or age>MAX_AGE_HOURS:stats["נפסלו ישנות"]+=1;continue
                s=score(title,age)
                if s<MIN_ALERT_SCORE:stats["ציון נמוך"]+=1;continue
                candidates.append((sym,title,url,s))
    verified=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures=[pool.submit(source_date,url) for _,_,url,_ in candidates]
        for item,f in zip(candidates,futures):
            sym,title,url,s=item; dt,final=f.result()
            if not dt:stats["ללא תאריך מקור"]+=1;continue
            age=(now-dt).total_seconds()/3600
            if age<0 or age>MAX_AGE_HOURS:stats["נפסלו ישנות"]+=1;continue
            stats["עברו תאריך RSS"]+=1
            ident=final.lower(); ev=event_key(title)
            if ident in day or any(isinstance(v,dict) and v.get("event")==ev for v in day.values()):stats["כפילויות"]+=1;continue
            day[ident]={"event":ev,"title":title,"published":dt.isoformat(),"source":final}
            verified.append((s,sym,title,dt,final))
    persist_state(state)
    best={}
    for row in verified:
        s,sym,*_=row
        if sym not in best or s>best[sym][0]:best[sym]=row
    selected=sorted(best.values(),key=lambda x:(x[0],x[1]),reverse=True)[:5]
    for s,sym,title,dt,url in selected:
        label,meaning=classify(title,s)
        msg=f"🇮🇱 OTC M — איתות חדש\n\n{label}\n\n💲 מניה: {sym}\n⭐ ציון: {s*10}/100\n🕒 פורסם במקור: {dt.strftime('%d/%m/%Y %H:%M')} UTC\n\n📰 אירוע:\n{title}\n\n🔗 קישור למקור:\n{url}\n\n💡 משמעות: {meaning}\n\n⚠️ מידע לצורכי בדיקה בלבד. אינו המלצה להשקעה ואינו מבטיח עלייה או ירידה."
        send_telegram(msg)
    print("OTC-M v8.3 — סיכום:",json.dumps(stats,ensure_ascii=False)); print(f"איתותים שנשלחו: {len(selected)}")

if __name__=="__main__":run_scanner()
