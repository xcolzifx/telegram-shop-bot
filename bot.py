import os
from telegram.ext import Application, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text(
        "🛍️ Welcome to our Shop!\n\n"
        "📦 Our shop is coming soon...\n"
        "✨ Please stay tuned!"
    )

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set!")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

print("🤖 Bot is running...")
app.run_polling()
