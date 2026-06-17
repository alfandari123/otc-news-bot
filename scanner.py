import json

WATCHLIST = [
    "AITX",
    "SONN",
    "GVSI",
    "HMBL",
    "ILUS",
    "ABQQ"
]

with open("watchlist.json", "w") as f:
    json.dump(WATCHLIST, f)
