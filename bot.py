import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set!")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛍️ SHOP", callback_data="shop")],
        [InlineKeyboardButton("📦 MY ORDERS", callback_data="orders")],
        [InlineKeyboardButton("📞 ADMIN SUPPORT", callback_data="support")],
    ]

    await update.message.reply_text(
        "🛍️ <b>WELCOME TO OUR SHOP!</b>\n\n"
        "✨ Choose an option below:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "shop":
        await query.edit_message_text(
            "🛍️ <b>SHOP</b>\n\n"
            "📦 Products will be added soon!",
            parse_mode="HTML",
        )

    elif query.data == "orders":
        await query.edit_message_text(
            "📦 <b>MY ORDERS</b>\n\n"
            "You don't have any orders yet.",
            parse_mode="HTML",
        )

    elif query.data == "support":
        await query.edit_message_text(
            "📞 <b>ADMIN SUPPORT</b>\n\n"
            "Contact the admin for help.",
            parse_mode="HTML",
        )


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))

print("🤖 Bot is running...")

app.run_polling()
