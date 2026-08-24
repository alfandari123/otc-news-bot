import csv
import io
import json
import time

import requests


API_URL = "https://www.otcmarkets.com/research/stock-screener/api"
CSV_URL = "https://www.otcmarkets.com/research/stock-screener/api/downloadCSV"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36",
    "Accept": "text/csv,application/json,text/plain,*/*",
    "Referer": "https://www.otcmarkets.com/research/stock-screener/",
}
MARKETS = "1,10,20,30,40,21"


def get_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def get_otc_stocks_from_csv(session):
    """Use OTC Markets' CSV download endpoint, which avoids the JSON decoding failure."""
    params = {
        "market": MARKETS,
        "pageSize": 10000,
    }
    response = session.get(CSV_URL, params=params, timeout=60)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()
    text = response.text.lstrip("\ufeff").strip()

    # A successful response must actually contain CSV data, not an HTML error/challenge page.
    if not text or "<html" in text[:500].lower() or "<!doctype" in text[:500].lower():
        raise RuntimeError(
            f"OTC CSV endpoint returned non-CSV data "
            f"(status={response.status_code}, content-type={content_type}, "
            f"preview={text[:150]!r})"
        )

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise RuntimeError("OTC CSV response has no header row")

    symbol_column = next(
        (name for name in reader.fieldnames if name and name.strip().lower() in {"symbol", "ticker"}),
        None,
    )
    if not symbol_column:
        raise RuntimeError(f"OTC CSV does not contain a Symbol/Ticker column: {reader.fieldnames}")

    stocks = []
    for row in reader:
        symbol = (row.get(symbol_column) or "").strip().upper()
        if symbol:
            stocks.append(symbol)

    return list(dict.fromkeys(stocks))


def get_otc_stocks_from_json(session):
    """Fallback to the screener JSON endpoint with retries and safe JSON handling."""
    stocks = []
    page = 1

    while page <= 200:
        params = {
            "market": MARKETS,
            "pageSize": 100,
            "page": page,
        }
        response = session.get(API_URL, params=params, timeout=30)
        response.raise_for_status()

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            preview = response.text[:200].replace("\n", " ")
            raise RuntimeError(
                f"OTC JSON endpoint returned non-JSON data "
                f"(status={response.status_code}, content-type={response.headers.get('content-type')}, "
                f"preview={preview!r})"
            ) from exc

        raw = data.get("stocks", [])
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, list) or not raw:
            break

        for item in raw:
            symbol = item.get("symbol") if isinstance(item, dict) else item
            if symbol:
                stocks.append(str(symbol).strip().upper())

        pages = int(data.get("pages", page))
        if page >= pages:
            break
        page += 1
        time.sleep(0.5)

    return list(dict.fromkeys(stocks))


def get_otc_stocks():
    session = get_session()

    # CSV is the primary path. The previous version failed because it assumed
    # every response from the JSON endpoint was JSON.
    try:
        stocks = get_otc_stocks_from_csv(session)
        if stocks:
            return stocks
        raise RuntimeError("OTC CSV returned zero symbols")
    except Exception as csv_error:
        print(f"CSV fetch failed: {csv_error}")
        print("Trying OTC JSON endpoint as fallback...")
        try:
            return get_otc_stocks_from_json(session)
        except Exception as json_error:
            raise RuntimeError(
                "Could not retrieve OTC stock list from either OTC Markets endpoint. "
                f"CSV error: {csv_error}; JSON error: {json_error}"
            ) from json_error


if __name__ == "__main__":
    stocks = get_otc_stocks()
    print("Found:", len(stocks))

    with open("otc_stocks.json", "w", encoding="utf-8") as f:
        json.dump(stocks, f, indent=2)

    print("OTC LIST UPDATED")
