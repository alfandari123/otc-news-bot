import json

def scan_otc():
    return ["AITX", "SONN", "GVSI"]

if __name__ == "__main__":
    data = scan_otc()

    with open("watchlist.json", "w") as f:
        json.dump(data, f)
