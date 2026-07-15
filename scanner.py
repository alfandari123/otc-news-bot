"""News lookup and message formatting for the OTC Telegram bot."""

from __future__ import annotations

import html
import json
import logging
import os
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus
from xml.etree import ElementTree

import requests

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent
WATCHLIST_FILE = ROOT / "watchlist.json"
RSS_TIMEOUT_SECONDS = 12
MAX_HEADLINES = 3


def _normalise_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol or len(symbol) > 12 or not symbol.replace(".", "").isalnum():
        raise ValueError("Symbol must contain only letters, digits, or a dot.")
    return symbol


def load_watchlist() -> list[str]:
    try:
        symbols = json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
        if not isinstance(symbols, list):
            raise ValueError("watchlist must be a JSON list")
        return sorted({_normalise_symbol(symbol) for symbol in symbols})
    except FileNotFoundError:
        return []
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        LOGGER.warning("Could not load watchlist: %s", exc)
        return []


def save_watchlist(symbols: Iterable[str]) -> list[str]:
    clean_symbols = sorted({_normalise_symbol(symbol) for symbol in symbols})
    temporary = WATCHLIST_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(clean_symbols, indent=2) + "\n", encoding="utf-8")
    temporary.replace(WATCHLIST_FILE)
    return clean_symbols


def fetch_news(symbol: str, limit: int = MAX_HEADLINES) -> list[tuple[str, str]]:
    """Return recent Google News RSS items for a ticker without an API key."""
    symbol = _normalise_symbol(symbol)
    url = "https://news.google.com/rss/search?q=" + quote_plus(f"{symbol} stock") + "&hl=en-US&gl=US&ceid=US:en"
    response = requests.get(url, timeout=RSS_TIMEOUT_SECONDS, headers={"User-Agent": "otc-news-bot/1.0"})
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    items: list[tuple[str, str]] = []
    for item in root.findall("./channel/item")[:limit]:
        title = html.unescape(item.findtext("title", "Untitled news item"))
        link = item.findtext("link", "")
        items.append((title, link))
    return items


def check(symbol: str) -> str:
    """Build the Telegram-ready status message for one symbol."""
    symbol = _normalise_symbol(symbol)
    try:
        headlines = fetch_news(symbol)
    except requests.RequestException as exc:
        LOGGER.warning("News lookup failed for %s: %s", symbol, exc)
        return f"⚠️ {symbol}\nUnable to retrieve news right now. Please try again shortly."
    except ElementTree.ParseError:
        return f"⚠️ {symbol}\nThe news feed returned an unreadable response."

    if not headlines:
        return f"📊 {symbol}\nNo recent news headlines found."

    lines = [f"📰 {symbol} — latest news"]
    for title, link in headlines:
        lines.append(f"• {title}\n{link}" if link else f"• {title}")
    return "\n\n".join(lines)


def scan_watchlist(symbols: Iterable[str] | None = None) -> str:
    """Build a bounded, Telegram-safe scan report for the configured symbols."""
    symbols = list(symbols) if symbols is not None else load_watchlist()
    if not symbols:
        return "📭 Watchlist is empty. Add a symbol with /add AITX."
    reports = [check(symbol) for symbol in symbols]
    message = "\n\n──────────\n\n".join(reports)
    return message[:4000] + ("\n…" if len(message) > 4000 else "")
