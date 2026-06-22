import feedparser

KEYWORDS = [
    "OTC stock",
    "OTCQB",
    "OTCQX",
    "Pink Current",
    "microcap stock",
    "penny stock"
]

candidates = set()

for keyword in KEYWORDS:

    feed = feedparser.parse(
        f"https://news.google.com/rss/search?q={keyword}"
    )

    for item in feed.entries:

        title = item.title.upper()

        words = title.split()

        for word in words:

            word = word.replace("(", "").replace(")", "")
            word = word.replace(",", "").replace(".", "")

            if (
                len(word) >= 3
                and len(word) <= 5
                and word.isalpha()
            ):
                candidates.add(word)

with open("market_watchlist.json", "w") as f:

    import json

    json.dump(
        sorted(list(candidates)),
        f,
        indent=2
    )

print(
    f"Found {len(candidates)} candidate symbols"
)
