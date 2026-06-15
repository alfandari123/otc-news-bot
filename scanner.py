import requests

def get_otc_movers():
    # דוגמה בלבד – כאן צריך API אמיתי בהמשך
    return ["AITX", "SONN", "GVSI"]

if __name__ == "__main__":
    stocks = get_otc_movers()

    with open("watchlist.json", "w") as f:
        import json
        json.dump(stocks, f)
