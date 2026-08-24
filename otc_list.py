import csv
import io
import json
import time
import requests

API_URL = "https://www.otcmarkets.com/research/stock-screener/api"
CSV_URL = "https://www.otcmarkets.com/research/stock-screener/api/downloadCSV"
FINRA_URL = "https://api.finra.org/data/group/otcMarket/name/OTCDAILYLIST"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv,application/json,text/plain,*/*"}
MARKETS = "1,10,20,30,40,21"
CACHE_FILE = "otc_stocks.json"

def get_session():
    s = requests.Session(); s.headers.update(HEADERS); return s

def get_otc_stocks_from_csv(s):
    r = s.get(CSV_URL, params={"market": MARKETS, "pageSize": 10000}, timeout=60); r.raise_for_status()
    t = r.text.lstrip("\ufeff").strip()
    if not t or "<html" in t[:500].lower() or "<!doctype" in t[:500].lower(): raise RuntimeError("OTC CSV unavailable")
    rows = csv.DictReader(io.StringIO(t)); col = next((x for x in (rows.fieldnames or []) if x and x.strip().lower() in {"symbol", "ticker"}), None)
    if not col: raise RuntimeError("OTC CSV has no Symbol/Ticker column")
    return list(dict.fromkeys((x.get(col) or "").strip().upper() for x in rows if (x.get(col) or "").strip()))

def get_otc_stocks_from_json(s):
    r = s.get(API_URL, params={"market": MARKETS, "pageSize": 10000, "page": 1}, timeout=30); r.raise_for_status()
    try: d = r.json()
    except requests.exceptions.JSONDecodeError as e: raise RuntimeError("OTC JSON unavailable") from e
    raw = d.get("stocks", []); raw = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(raw, list): raise RuntimeError("Unexpected OTC JSON")
    return list(dict.fromkeys(str(x.get("symbol") if isinstance(x, dict) else x).strip().upper() for x in raw if x))

def get_otc_stocks_from_finra(s):
    r = s.get(FINRA_URL, params={"limit": 10000}, timeout=60); r.raise_for_status(); d = r.json()
    out = []
    for x in d if isinstance(d, list) else []:
        for k in ("newSymbolCode", "oldSymbolCode"):
            if x.get(k): out.append(str(x[k]).strip().upper())
    return list(dict.fromkeys(out))

def get_cached():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f: d = json.load(f)
        return list(dict.fromkeys(str(x).strip().upper() for x in d if x)) if isinstance(d, list) else []
    except (OSError, ValueError, TypeError): return []

def get_otc_stocks():
    s = get_session(); errors = []
    for name, fn in (("OTC CSV", get_otc_stocks_from_csv), ("OTC JSON", get_otc_stocks_from_json), ("FINRA", get_otc_stocks_from_finra)):
        try:
            stocks = fn(s)
            if stocks:
                print(f"Using {name}: {len(stocks)} symbols")
                return stocks
        except Exception as e:
            errors.append(f"{name}: {e}"); print(f"{name} failed: {e}")
        time.sleep(1)
    cached = get_cached()
    if cached:
        print(f"Using cached OTC list: {len(cached)} symbols")
        return cached
    raise RuntimeError("No OTC source available: " + " | ".join(errors))

if __name__ == "__main__":
    stocks = get_otc_stocks(); print("Found:", len(stocks))
    with open(CACHE_FILE, "w", encoding="utf-8") as f: json.dump(stocks, f, indent=2)
    print("OTC LIST UPDATED")
