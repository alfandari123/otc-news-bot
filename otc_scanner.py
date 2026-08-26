import os, json, re, base64, requests, feedparser
from datetime import datetime, timezone
from urllib.parse import quote
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BOT_TOKEN=os.getenv("BOT_TOKEN"); CHAT_ID=os.getenv("CHAT_ID"); GITHUB_TOKEN=os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY=os.getenv("GITHUB_REPOSITORY","alfandari123/otc-news-bot"); SEEN_FILE="seen_news.json"
MAX_AGE_HOURS=72; RSS_FALLBACK_HOURS=48; MIN_ALERT_SCORE=2; MAX_STOCKS=250; MAX_NEWS_PER_SYMBOL=5
POSITIVE={"contract":4,"contracts":4,"partnership":4,"acquisition":5,"merger":6,"fda":5,"approval":5,"approved":5,"revenue":3,"profit":4,"growth":3,"orders":4,"agreement":4,"expansion":3,"launch":3,"launched":3,"definitive agreement":6,"purchase agreement":6,"strategic mou":3,"secures":4,"secured":4,"deal":3,"license":4,"licence":4,"supply":3,"sales":3,"financing":2,"funding":3,"investment":3,"commercial":3,"production":3,"customer":3,"customers":3,"award":4,"awarded":4,"backlog":3,"milestone":3,"cleared":5}
FUTURE={"clinical":3,"trial":3,"phase":3,"pipeline":3,"development":2,"strategic":2,"potential":2,"plans":2,"expected":2,"study":2,"program":2,"technology":2,"pilot":2}
NEGATIVE={"dilution":-5,"reverse split":-5,"bankruptcy":-10,"going concern":-7,"lawsuit":-5,"offering":-4,"toxic":-5,"default":-6,"delisting":-6}
EVENT_VERBS=("announces","announced","signs","signed","enters","entered","launches","launched","reports","reported","receives","received","wins","won","secures","secured","completes","completed","closes","closed","approves","approved","cleared","awarded","appoints","appointed","files","filed","submits","submitted","initiates","initiated","acquires","acquired","agrees","agreed")
ANALYSIS_WORDS=("inside","outlook","analysis","final chapter","what investors","investor take","deep dive","review","explained","explainer","commentary","opinion","why it matters","looking ahead")

def parse_date(v):
    if not v:return None
    for fn in (lambda x:datetime.fromisoformat(str(x).replace("Z","+00:00")),parsedate_to_datetime):
        try:
            d=fn(v); return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
        except Exception: pass
    return None

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID: raise RuntimeError("חסרים BOT_TOKEN או CHAT_ID")
    r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":text,"disable_web_page_preview":False},timeout=20)
    r.raise_for_status(); data=r.json()
    if not data.get("ok"): raise RuntimeError(f"Telegram API error: {data}")

def load_state():
    try:
        with open(SEEN_FILE,encoding="utf-8") as f:
            d=json.load(f); return d if isinstance(d,dict) else {}
    except Exception: pass
    if GITHUB_TOKEN:
        try:
            u=f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{SEEN_FILE}"; h={"Authorization":f"Bearer {GITHUB_TOKEN}"}
            r=requests.get(u,headers=h,timeout=10)
            if r.status_code==200:return json.loads(base64.b64decode(r.json()["content"]).decode())
        except Exception as e: print(f"שגיאה בטעינת היסטוריה: {e}")
    return {}

def save_state(d):
    with open(SEEN_FILE,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
    if not GITHUB_TOKEN:return
    try:
        h={"Authorization":f"Bearer {GITHUB_TOKEN}","Accept":"application/vnd.github+json"}; u=f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{SEEN_FILE}"
        old=requests.get(u,headers=h,timeout=10); p={"message":"Update OTC alert history","content":base64.b64encode(json.dumps(d,ensure_ascii=False,indent=2).encode()).decode()}
        if old.status_code==200:p["sha"]=old.json()["sha"]
        requests.put(u,headers=h,json=p,timeout=10)
    except Exception as e: print(f"שגיאה בשמירת היסטוריה: {e}")

def resolve_source(url):
    try:
        r=requests.get(url,timeout=10,headers={"User-Agent":"Mozilla/5.0 (compatible; OTC-M scanner)"},allow_redirects=True)
        return r.url,r.text[:1500000] if r.status_code==200 else ""
    except Exception:return url,""

def source_date(url):
    final,html=resolve_source(url)
    if not html:return None,final
    patterns=[r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|datePublished|datecreated|publish(?:ed)?|publication_date|parsely-pub-date)["\'][^>]+content=["\']([^"\']+)',r'"datePublished"\s*:\s*"([^"]+)"',r'<time[^>]+datetime=["\']([^"\']+)["\']']
    dates=[]
    for p in patterns:
        for x in re.findall(p,html,re.I):
            d=parse_date(x)
            if d:dates.append(d)
    return (min(dates),final) if dates else (None,final)

def recycled(title):
    t=title.lower(); return any(x in t for x in ANALYSIS_WORDS) and not any(x in t for x in EVENT_VERBS)

def score(title,age):
    t=title.lower(); s=sum(p for w,p in POSITIVE.items() if w in t)+sum(p for w,p in FUTURE.items() if w in t)+sum(p for w,p in NEGATIVE.items() if w in t)
    if any(v in t for v in EVENT_VERBS):s+=2
    if age<=24:s+=2
    elif age>48:s-=1
    if recycled(title):s-=7
    return max(0,min(10,s))

def classify(title,s):
    t=title.lower()
    if s>=8 and any(v in t for v in EVENT_VERBS):return "🟢 חדשות חיוביות מאוד","אירוע חדש ומשמעותי שעשוי להשפיע בטווח הקצר"
    if s>=5 or any(x in t for x in FUTURE):return "🟡 חדשות עם פוטנציאל עתידי","אירוע שעשוי להיות חיובי בהמשך אך עדיין אינו ודאי"
    return "🔵 חדשות למעקב","מידע חדש שדורש מעקב ובדיקה"

def discover(symbol):
    try:
        u=f'https://news.google.com/rss/search?q={quote(symbol+" OTC stock when:3d")}&hl=en-US&gl=US&ceid=US:en'; r=requests.get(u,timeout=8,headers={"User-Agent":"OTC-M scanner"})
        return symbol,feedparser.parse(r.content).entries[:MAX_NEWS_PER_SYMBOL]
    except Exception as e: print(f"שגיאת חדשות {symbol}: {e}"); return symbol,[]

def event_key(title):
    t=re.sub(r"[^a-z0-9]+"," ",title.lower())
    for w in ("otc","stock","corp","corporation","plc","company","announces","announcement","news","press release"):t=t.replace(w," ")
    return " ".join(t.split()[:45])

def run_scanner():
    with open("otc_stocks.json",encoding="utf-8") as f:stocks=json.load(f)
    stocks=[str(x).upper().strip() for x in stocks if str(x).strip()][:MAX_STOCKS]
    state=load_state(); today=datetime.now(timezone.utc).date().isoformat(); day=state.setdefault(today,{})
    now=datetime.now(timezone.utc); candidates=[]
    stats={"מניות שנסרקו":0,"כתבות RSS":0,"עברו בדיקת RSS":0,"עברו אימות מקור":0,"השתמשו ב-RSS כגיבוי":0,"נפסלו ישנות":0,"נפסלו כתבות ניתוח":0,"ציון נמוך":0,"כפילויות":0}
    with ThreadPoolExecutor(max_workers=25) as pool:
        for future in as_completed([pool.submit(discover,s) for s in stocks]):
            sym,items=future.result(); stats["מניות שנסרקו"]+=1
            for item in items:
                stats["כתבות RSS"]+=1; title=item.get("title","").strip(); link=item.get("link","").strip(); rss=parse_date(item.get("published") or item.get("updated"))
                if not title or not link or not rss:continue
                if recycled(title):stats["נפסלו כתבות ניתוח"]+=1;continue
                age=(now-rss).total_seconds()/3600
                if age<0 or age>MAX_AGE_HOURS:stats["נפסלו ישנות"]+=1;continue
                stats["עברו בדיקת RSS"]+=1; s=score(title,age)
                if s<MIN_ALERT_SCORE:stats["ציון נמוך"]+=1;continue
                candidates.append((sym,title,link,s,rss))
    verified=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        for item,future in zip(candidates,[pool.submit(source_date,x[2]) for x in candidates]):
            sym,title,link,s,rss=item; dt,final=future.result(); date_source="מקור"
            if dt is None:
                dt=rss; date_source="RSS"; age=(now-dt).total_seconds()/3600
                if age<0 or age>RSS_FALLBACK_HOURS:stats["נפסלו ישנות"]+=1;continue
                stats["השתמשו ב-RSS כגיבוי"]+=1
            else:
                age=(now-dt).total_seconds()/3600
                if age<0 or age>MAX_AGE_HOURS:stats["נפסלו ישנות"]+=1;continue
                stats["עברו אימות מקור"]+=1
            key=final.lower(); ev=event_key(title)
            if key in day or any(isinstance(v,dict) and v.get("event")==ev for v in day.values()):stats["כפילויות"]+=1;continue
            day[key]={"event":ev,"title":title,"published":dt.isoformat(),"source":final,"date_source":date_source}; verified.append((s,sym,title,dt,final,date_source))
    save_state(state)
    best={}
    for row in verified:
        if row[1] not in best or row[0]>best[row[1]][0]:best[row[1]]=row
    selected=sorted(best.values(),key=lambda x:(x[0],x[1]),reverse=True)[:5]
    for s,sym,title,dt,url,date_source in selected:
        label,meaning=classify(title,s); verify="🛡️ מקור ותאריך הכתבה אומתו" if date_source=="מקור" else "🛡️ המקור קיים; תאריך הפרסום נלקח מ-RSS כי האתר לא חשף תאריך"
        msg=f"🇮🇱 OTC M — איתות חדש\n\n{label}\n\n💲 מניה: ${sym}\n⭐ ציון: {s*10}/100\n🕒 תאריך פרסום: {dt.strftime('%d/%m/%Y %H:%M')} UTC\n\n📰 אירוע:\n{title}\n\n{verify}\n🔗 קישור ישיר למקור:\n{url}\n\n💡 משמעות: {meaning}\n\n⚠️ מידע לצורכי בדיקה בלבד. אינו המלצה להשקעה ואינו מבטיח עלייה או ירידה."
        send_telegram(msg)
    print("OTC-M v11.0 — סיכום:",json.dumps(stats,ensure_ascii=False)); print(f"איתותים שנשלחו: {len(selected)}")

if __name__=="__main__":run_scanner()
