def get_stock_data(symbol):

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.OB"

    try:
        response = requests.get(url).json()

        result = response["chart"]["result"][0]

        price = result["meta"]["regularMarketPrice"]

        return price

    except:
        return None
