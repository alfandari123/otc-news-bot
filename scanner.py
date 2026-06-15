import json

with open("watchlist.json", "r") as f:
    watchlist = json.load(f)

print("WATCHLIST:")
print(watchlist)
