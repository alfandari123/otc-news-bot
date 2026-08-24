import json
import time

import requests


URL = "https://www.otcmarkets.com/research/stock-screener/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.otcmarkets.com/research/stock-screener/",
}


def get_otc_stocks():
    stocks = []
    page = 1

    while page <= 200:
        params = {
            "market": "1,10,20,30,40,21",
            "pageSize": 100,
            "page": page,
        }
        response = requests.get(URL, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        raw = data.get("stocks", [])
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, list) or not raw:
            break

        for item in raw:
            if isinstance(item, dict):
                symbol = item.get("symbol")
            else:
                symbol = item
            if symbol:
                stocks.append(str(symbol).strip().upper())

        pages = int(data.get("pages", page))
        if page >= pages:
            break
        page += 1
        time.sleep(0.25)

    # Remove duplicates while preserving order.
    return list(dict.fromkeys(stocks))


stocks = get_otc_stocks()
print("Found:", len(stocks))

with open("otc_stocks.json", "w", encoding="utf-8") as f:
    json.dump(stocks, f, indent=2)

print("OTC LIST UPDATED")