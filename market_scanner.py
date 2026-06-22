import requests

url = "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"

response = requests.get(url, timeout=10)

print("STATUS:", response.status_code)
print(response.text[:1000])
