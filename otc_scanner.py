import os,json,re,base64,requests,feedparser
from datetime import datetime,timezone
from urllib.parse import quote
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor,as_completed

BOT_TOKEN=os.getenv("BOT_TOKEN"); CHAT_ID=os.getenv("CHAT_ID"); GITHUB_TOKEN=os.getenv("GITHUB_TOKEN")
REPO=os.getenv("GITHUB_REPOSITORY","alfandari123/otc-news-bot"); SEEN_FILE="seen_news.json"
MAX_AGE=72; RSS_FALLBACK=48; MIN_SCORE=2; MAX_STOCKS=250; MAX_NEWS=8

POS={"contract":4,"contracts":4,"partnership":4,"acquisition":5,"merger":6,"fda":5,"approval":5,"approved":5,"revenue":3,"profit":4,"growth":3,"orders":4,"agreement":4,"expansion":3,"launch":3,"launched":3,"definitive agreement":6,"purchase agreement":6,"strategic mou":3,"secures":4,"secured":4,"deal":3,"license":4,"licence":4,"supply":3,"sales":3,"financing":2,"funding":3,"investment":3,"commercial":3,"production":3,"customer":3,"customers":3,"award":4,"awarded":4,"backlog":3,"milestone":3,"cleared":5}
FUTURE={"clinical":3,"trial":3,"phase":3,"pipeline":3,"development":2,"strategic":2,"potential":2,"plans":2,"expected":2,"study":2,"program":2,"technology":2,"pilot":2}
NEG={"dilution":-5,"reverse split":-5,"bankruptcy":-10,"going concern":-7,"lawsuit":-5,"offering":-4,"toxic":-5,"default":-6,"delisting":-6}
VERBS=("announces","announced","signs","signed","enters","entered","launches","launched","reports","reported","receives","received","wins","won","secures","secured","completes","completed","closes","closed","approves","approved","cleared","awarded","appoints","appointed","files","filed","submits","submitted","initiates","initiated","acquires","acquired","agrees","agreed")
ANALYSIS=("inside","outlook","analysis","final chapter","what investors","investor take","deep dive","review","explained","explainer","commentary","opinion","why it matters","looking ahead")
SOURCE_DOMAINS={"OTC Markets":"otcmarkets.com","GlobeNewswire":"globenewswire.com","PR Newswire":"prnewswire.com","Business Wire":"businesswire.com","SEC":"sec.gov"}

def parse_date(v):
    if not v:return None
    for fn in (lambda x:datetime.fromisoformat(str(x).replace("Z","+00:00")),parsedate_to_datetime):
        try:
            d=fn(v); return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
        except:pass
    return None

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:raise RuntimeError("חסרים BOT_TOKEN או CHAT_ID")
    r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":text,"disable_web_page_preview":False},timeout=20); r.raise_for_status()
    data=r.json()
    if not data.get("ok"):raise RuntimeError(f"Telegram API error: {data}")

def load_state():
    try:
        with open(SEEN_FILE,encoding="utf-8") as f:return json.load(f)
    except:pass
    if GITHUB_TOKEN:
        try:
            u=f"https://api.github.com/repos/{REPO}/contents/{SEEN_FILE}"; r=requests.get(u,headers={"Authorization":f"Bearer {GITHUB_TOKEN}"},timeout=10)
            if r.status_code==200:return json.loads(base64.b64decode(r.json()["content"]).decode())
        except:pass
    return {}

def save_state(d):
    with open(SEEN_FILE,"w",encoding="utf-8") as f:json.dump(d,f,ensure_ascii=False,indent=2)
    if not GITHUB_TOKEN:return
    try:
        h={"Authorization":f"Bearer {GITHUB_TOKEN}","Accept":"application/vnd.github+json"}; u=f"https://api.github.com/repos/{REPO}/contents/{SEEN_FILE}"
        old=requests.get(u,headers=h,timeout=10); p={"message":"Update OTC alert history","content":base64.b64encode(json.dumps(d,ensure_ascii=False,indent=2).encode()).decode()}
        if old.status_code==200:p["sha"]=old.json()["sha"]
        requests.put(u,headers=h,json=p,timeout=10)
    except Exception as e:print(f"שגיאת שמירת היסטוריה: {e}")

def recycled(t):
    t=t.lower(); return any(x in t for x in ANALYSIS) and not any(v in t for v in VERBS)

def score(t,age):
    x=t.lower(); s=sum(v for k,v in POS.items() if k in x)+sum(v for k,v in FUTURE.items() if k in x)+sum(v for k,v in NEG.items() if k in x)
    if any(v in x for v in VERBS):s+=2
    if age<=24:s+=2
    elif age>48:s-=1
    if recycled(t):s-=7
    return max(0,min(10,s))

def resolve(url):
    try:
        r=requests.get(url,timeout=10,headers={"User-Agent":"Mozilla/5.0 (compatible; OTC-M scanner)"},allow_redirects=True)
        return r.url,(r.text[:1500000] if r.status_code==200 else "")
    except:return url,""

def source_date(url):
    final,html=resolve(url)
    if not html:return None,final
    pats=[r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|datePublished|datecreated|publish(?:ed)?|publication_date|parsely-pub-date)["\'][^>]+content=["\']([^"\']+)',r'"datePublished"\s*:\s*"([^"]+)"',r'<time[^>]+datetime=["\']([^"\']+)["\']']
    ds=[]
    for p in pats:
        for x in re.findall(p,html,re.I):
            d=parse_date(x)
            if d:ds.append(d)
    return (min(ds),final) if ds else (None,final)

def discover(symbol):
    queries=[f'"{symbol}" OTC stock when:3d']
    for domain in SOURCE_DOMAINS.values():queries.append(f'"{symbol}" site:{domain} when:3d')
    # OTC Markets is the primary OTC-specific source; the other queries add independent publishers.
    entries={}
    for q in queries:
        try:
            u=f'https://news.google.com/rss/search?q={quote(q)}&hl=en-US&gl=US&ceid=US:en'; r=requests.get(u,timeout=8,headers={"User-Agent":"OTC-M scanner/12.0"})
            for e in feedparser.parse(r.content).entries[:MAX_NEWS]:
                link=e.get("link",""); title=e.get("title","")
                if link and title:entries[link]=(e,q)
        except Exception as e:print(f"שגיאת מקור {symbol}: {e}")
    return symbol,[e for e,_ in entries.values()]

def event_key(t):
    x=re.sub(r"[^a-z0-9]+"," ",t.lower())
    for w in ("otc","stock","corp","corporation","plc","company","announces","announcement","news","press release"):x=x.replace(w," ")
    return " ".join(x.split()[:45])

def source_name(url):
    u=url.lower()
    for n,d in SOURCE_DOMAINS.items():
        if d in u:return n
    return "מקור חדשות נוסף"

def run_scanner():
    with open("otc_stocks.json",encoding="utf-8") as f:stocks=json.load(f)
    stocks=[str(x).upper().strip() for x in stocks if str(x).strip()][:MAX_STOCKS]
    state=load_state(); today=datetime.now(timezone.utc).date().isoformat(); day=state.setdefault(today,{})
    now=datetime.now(timezone.utc); candidates=[]
    stats={"מניות":0,"כתבות":0,"עברו RSS":0,"אומתו במקור":0,"RSS גיבוי":0,"נפסלו ישנות":0,"ניתוח":0,"ציון נמוך":0,"כפילויות":0,"מקורות":{}}
    with ThreadPoolExecutor(max_workers=20) as pool:
        for fut in as_completed([pool.submit(discover,s) for s in stocks]):
            sym,items=fut.result();stats["מניות"]+=1
            for item in items:
                stats["כתבות"]+=1; title=item.get("title","").strip(); link=item.get("link","").strip(); rss=parse_date(item.get("published") or item.get("updated"))
                if not title or not link or not rss:continue
                if recycled(title):stats["ניתוח"]+=1;continue
                age=(now-rss).total_seconds()/3600
                if age<0 or age>MAX_AGE:stats["נפסלו ישנות"]+=1;continue
                stats["עברו RSS"]+=1; s=score(title,age)
                if s<MIN_SCORE:stats["ציון נמוך"]+=1;continue
                candidates.append((sym,title,link,s,rss))
    verified=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures=[pool.submit(source_date,x[2]) for x in candidates]
        for item,fut in zip(candidates,futures):
            sym,title,link,s,rss=item; dt,final=fut.result(); date_src="מקור"
            if dt is None:
                dt=rss;date_src="RSS"
                if (now-dt).total_seconds()/3600>RSS_FALLBACK:stats["נפסלו ישנות"]+=1;continue
                stats["RSS גיבוי"]+=1
            else:
                age=(now-dt).total_seconds()/3600
                if age<0 or age>MAX_AGE:stats["נפסלו ישנות"]+=1;continue
                stats["אומתו במקור"]+=1
            sn=source_name(final);stats["מקורות"][sn]=stats["מקורות"].get(sn,0)+1
            ev=event_key(title); key=final.lower()
            if key in day or any(isinstance(v,dict) and v.get("event")==ev for v in day.values()):stats["כפילויות"]+=1;continue
            day[key]={"event":ev,"title":title,"published":dt.isoformat(),"source":final};verified.append((s,sym,title,dt,final,date_src,sn))
    save_state(state)
    best={}
    for row in verified:
        if row[1] not in best or row[0]>best[row[1]][0]:best[row[1]]=row
    selected=sorted(best.values(),key=lambda x:(x[0],x[1]),reverse=True)[:5]
    for s,sym,title,dt,url,date_src,sn in selected:
        if s>=8:label="🟢 חדשות חיוביות מאוד";meaning="אירוע חדש ומשמעותי שעשוי להשפיע בטווח הקצר"
        elif s>=5 or any(x in title.lower() for x in FUTURE):label="🟡 חדשות עם פוטנציאל עתידי";meaning="אירוע שעשוי להיות חיובי בהמשך אך עדיין אינו ודאי"
        else:label="🔵 חדשות למעקב";meaning="מידע חדש שדורש מעקב ובדיקה"
        verify="🛡️ המקור ותאריך הכתבה אומתו" if date_src=="מקור" else "🛡️ המקור קיים; תאריך הפרסום נלקח מ-RSS כי האתר לא חשף תאריך"
        msg=f"🇮🇱 OTC M — איתות חדש\n\n{label}\n\n💲 מניה: ${sym}\n⭐ ציון: {s*10}/100\n🕒 תאריך פרסום: {dt.strftime('%d/%m/%Y %H:%M')} UTC\n🏷️ מקור: {sn}\n\n📰 אירוע:\n{title}\n\n{verify}\n🔗 קישור ישיר למקור:\n{url}\n\n💡 משמעות: {meaning}\n\n⚠️ מידע לצורכי בדיקה בלבד. אינו המלצה להשקעה ואינו מבטיח עלייה או ירידה."
        send_telegram(msg)
    print("OTC-M v12.0 — סיכום:",json.dumps(stats,ensure_ascii=False));print(f"איתותים שנשלחו: {len(selected)}")

if __name__=="__main__":run_scanner()
