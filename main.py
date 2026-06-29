import os
import json

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)


BOT_TOKEN = os.getenv("BOT_TOKEN")

WATCHLIST_FILE = "watchlist.json"



def load_watchlist():

    try:

        with open(WATCHLIST_FILE, "r") as f:
            return json.load(f)

    except:

        return []



def save_watchlist(data):

    with open(WATCHLIST_FILE, "w") as f:

        json.dump(
            data,
            f,
            indent=2
        )



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🚀 OTC Agent Online\n\n"
        "/add SYMBOL\n"
        "/remove SYMBOL\n"
        "/list\n"
        "/check SYMBOL"
    )



async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:

        await update.message.reply_text(
            "Usage: /add AITX"
        )

        return


    symbol = context.args[0].upper()


    watchlist = load_watchlist()


    if symbol not in watchlist:

        watchlist.append(symbol)

        save_watchlist(watchlist)


    await update.message.reply_text(
        f"✅ Added {symbol}"
    )



async def remove_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:

        return


    symbol = context.args[0].upper()


    watchlist = load_watchlist()


    if symbol in watchlist:

        watchlist.remove(symbol)

        save_watchlist(watchlist)


    await update.message.reply_text(
        f"❌ Removed {symbol}"
    )



async def list_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):

    watchlist = load_watchlist()


    if not watchlist:

        await update.message.reply_text(
            "Watchlist is empty"
        )

        return



    text = (
        "📈 Watchlist\n\n"
        +
        "\n".join(watchlist)
    )


    await update.message.reply_text(
        text
    )



async def check_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:

        await update.message.reply_text(
            "Usage: /check AITX"
        )

        return



    symbol = context.args[0].upper()


    import scanner


    result = scanner.check(symbol)



    await update.message.reply_text(
        result
    )



async def scan_all(update: Update, context: ContextTypes.DEFAULT_TYPE):

    import scanner


    watchlist = load_watchlist()


    if not watchlist:

        await update.message.reply_text(
            "Watchlist empty"
        )

        return



    result = scanner.scan_watchlist(
        watchlist
    )


    await update.message.reply_text(
        result
    )



app = Application.builder().token(
    BOT_TOKEN
).build()



app.add_handler(
    CommandHandler("start", start)
)


app.add_handler(
    CommandHandler("add", add_stock)
)


app.add_handler(
    CommandHandler("remove", remove_stock)
)


app.add_handler(
    CommandHandler("list", list_stocks)
)


app.add_handler(
    CommandHandler("check", check_stock)
)


app.add_handler(
    CommandHandler("scan", scan_all)
)



app.run_polling()

import otc_list
