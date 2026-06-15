import json

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)

print("=== WATCHLIST ===")

for symbol in watchlist:
    print(f"Checking {symbol}")
