import csv
import io
import json
import requests

# Primary source: a maintained public ticker database with an OTC venue column.
# OTC Markets is kept as an optional secondary source, but the scanner no longer
# depends on OTC Markets being available.
BACKUP_URL = "https://raw.githubusercontent.com/adanos-software/free-ticker-database/main/data/listings.csv"
OTC_CSV_URL = "https://www.otcmarkets.com/research/stock-screener/api/downloadCSV"
CACHE_FILE = "otc_stocks.json"
HEADERS = {"User-Agent": "otc-news-bot/1.0", "Accept": "text/csv,text/plain,*/*"}


def get_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def clean_symbols(values):
    out = []
    seen = set()
    for value in values:
        symbol = str(value or "").strip().upper()
        if symbol and symbol not in seen:
            seen.add(symbol)
            out.append(symbol)
    return out


def get_from_backup(s):
    r = s.get(BACKUP_URL, timeout=90)
    r.raise_for_status()
    text = r.text.lstrip("\ufeff")
    if not text or text.lstrip().lower().startswith("<!doctype") or "<html" in text[:500].lower():
        raise RuntimeError("backup database returned HTML instead of CSV")

    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames or []
    ticker_col = next((x for x in fields if x and x.strip().lower() == "ticker"), None)
    exchange_col = next((x for x in fields if x and x.strip().lower() == "exchange"), None)
    asset_col = next((x for x in fields if x and x.strip().lower() == "asset_type"), None)
    if not ticker_col or not exchange_col:
        raise RuntimeError(f"backup CSV missing required columns: {fields[:10]}")

    symbols = []
    for row in reader:
        exchange = (row.get(exchange_col) or "").strip().upper()
        asset = (row.get(asset_col) or "").strip().lower() if asset_col else ""
        # Keep actual OTC stock listings, not ETFs or unrelated venues.
        if exchange == "OTC" and (not asset_col or asset == "stock"):
            symbols.append(row.get(ticker_col))

    symbols = clean_symbols(symbols)
    if len(symbols) < 100:
        raise RuntimeError(f"backup database returned too few OTC symbols: {len(symbols)}")
    return symbols


def get_from_otc(s):
    r = s.get(OTC_CSV_URL, params={"market": "1,10,20,30,40,21", "pageSize": 10000}, timeout=60)
    r.raise_for_status()
    text = r.text.lstrip("\ufeff").strip()
    if not text or "<html" in text[:500].lower() or "<!doctype" in text[:500].lower():
        raise RuntimeError("OTC Markets is temporarily unavailable")
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames or []
    col = next((x for x in fields if x and x.strip().lower() in {"symbol", "ticker"}), None)
    if not col:
        raise RuntimeError("OTC Markets CSV has no Symbol/Ticker column")
    symbols = clean_symbols(row.get(col) for row in reader)
    if not symbols:
        raise RuntimeError("OTC Markets returned zero symbols")
    return symbols


def get_cached():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return clean_symbols(data) if isinstance(data, list) else []
    except (OSError, ValueError, TypeError):
        return []


def get_otc_stocks():
    s = get_session()

    # Use the stable backup first. This prevents a temporary OTC Markets outage
    # from stopping the scanner entirely.
    for name, fn in (("backup database", get_from_backup), ("OTC Markets", get_from_otc)):
        try:
            stocks = fn(s)
            print(f"Using {name}: {len(stocks)} symbols")
            return stocks
        except Exception as e:
            print(f"{name} failed: {e}")

    cached = get_cached()
    if cached:
        print(f"Using cached OTC list: {len(cached)} symbols")
        return cached

    raise RuntimeError("No OTC stock list is available from backup, OTC Markets, or cache")


if __name__ == "__main__":
    stocks = get_otc_stocks()
    print("Found:", len(stocks))
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(stocks, f, indent=2)
    print("OTC LIST UPDATED")
