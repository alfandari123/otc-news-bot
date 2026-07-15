"""Telegram entry point for the OTC news bot."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

import scanner

ROOT = Path(__file__).resolve().parent
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
LOGGER = logging.getLogger(__name__)


def load_dotenv() -> None:
    """Tiny dependency-free .env reader; production hosts may use environment variables."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


async def reply(update: Update, text: str) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply(update, "🚀 OTC News Bot is online.\n\n/add SYMBOL\n/remove SYMBOL\n/list\n/check SYMBOL\n/scan")


async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await reply(update, "Usage: /add AITX")
        return
    try:
        symbols = scanner.load_watchlist()
        symbol = context.args[0].upper()
        scanner.save_watchlist([*symbols, symbol])
        await reply(update, f"✅ Added {symbol}.")
    except ValueError as exc:
        await reply(update, f"⚠️ {exc}")


async def remove_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await reply(update, "Usage: /remove AITX")
        return
    symbol = context.args[0].upper()
    try:
        current = scanner.load_watchlist()
        updated = scanner.save_watchlist(item for item in current if item != symbol)
        await reply(update, f"🗑️ Removed {symbol}." if symbol not in updated and symbol in current else f"{symbol} is not in the watchlist.")
    except ValueError as exc:
        await reply(update, f"⚠️ {exc}")


async def list_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    symbols = scanner.load_watchlist()
    await reply(update, "📈 Watchlist\n\n" + "\n".join(f"• {symbol}" for symbol in symbols) if symbols else "📭 Watchlist is empty.")


async def check_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await reply(update, "Usage: /check AITX")
        return
    try:
        result = await asyncio.to_thread(scanner.check, context.args[0])
        await reply(update, result)
    except ValueError as exc:
        await reply(update, f"⚠️ {exc}")


async def scan_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply(update, "🔎 Scanning watchlist…")
    await reply(update, await asyncio.to_thread(scanner.scan_watchlist))


async def scheduled_scan(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = os.getenv("CHAT_ID")
    if chat_id:
        await context.bot.send_message(chat_id=chat_id, text=await asyncio.to_thread(scanner.scan_watchlist), disable_web_page_preview=True)


def build_application() -> Application:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token or token.startswith("replace_"):
        raise RuntimeError("BOT_TOKEN is missing. Copy .env.example to .env and set BOT_TOKEN.")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_stock))
    app.add_handler(CommandHandler("remove", remove_stock))
    app.add_handler(CommandHandler("list", list_stocks))
    app.add_handler(CommandHandler("check", check_stock))
    app.add_handler(CommandHandler("scan", scan_all))
    interval = os.getenv("SCAN_INTERVAL_MINUTES")
    if interval and os.getenv("CHAT_ID"):
        app.job_queue.run_repeating(scheduled_scan, interval=float(interval) * 60, first=10, name="scheduled_scan")
    return app


if __name__ == "__main__":
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)
