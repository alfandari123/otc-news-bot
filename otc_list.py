import requests
import json


def get_otc_stocks():

    url = "https://www.otcmarkets.com/research/stock-screener/api/stock-screener"


    headers = {
        "User-Agent": "Mozilla/5.0"
    }


    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )


        data = response.json()


        stocks = []


        for item in data.get("data", []):

            symbol = item.get("symbol")


            if symbol:

                stocks.append(symbol)



        return stocks



    except Exception as e:

        print(
            "Error:",
            e
        )

        return []





stocks = get_otc_stocks()


print(
    f"Found {len(stocks)} stocks"
)



with open(
    "otc_stocks.json",
    "w"
) as f:


    json.dump(
        stocks,
        f,
        indent=2
    )
