import requests


def get_otc_stocks():

    url = "https://www.otcmarkets.com/research/stock-screener"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }


    response = requests.get(
        url,
        headers=headers,
        timeout=10
    )


    if response.status_code != 200:

        return []


    return []



stocks = get_otc_stocks()


print(stocks)
