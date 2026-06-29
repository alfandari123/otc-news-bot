import yfinance as yf


def get_market_data(symbol):

    try:

        ticker = yf.Ticker(symbol)

        info = ticker.fast_info


        price = info.get(
            "last_price",
            "N/A"
        )


        volume = info.get(
            "last_volume",
            "N/A"
        )


        return {
            "price": price,
            "volume": volume
        }


    except Exception as e:

        return {
            "price": "N/A",
            "volume": "N/A"
        }
