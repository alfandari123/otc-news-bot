import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

watchlist = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 OTC Agent Online\n\n"
        "/add SYMBOL\n"
        "/remove SYMBOL\n"
        "/list"
    )

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /add AITX")
        return

    symbol = context.args[0].upper()

    if symbol not in watchlist:
        watchlist.append(symbol)

    await update.message.reply_text(f"✅ Added {symbol}")

async def remove_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return

    symbol = context.args[0].upper()

    if symbol in watchlist:
        watchlist.remove(symbol)

    await update.message.reply_text(f"❌ Removed {symbol}")

async def list_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not watchlist:
        await update.message.reply_text("Watchlist is empty")
        return

    text = "📈 Watchlist\n\n" + "\n".join(watchlist)

    await update.message.reply_text(text)

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add_stock))
app.add_handler(CommandHandler("remove", remove_stock))
app.add_handler(CommandHandler("list", list_stocks))

app.run_polling()
