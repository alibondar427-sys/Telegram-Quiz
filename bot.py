import os
import asyncio
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text('✅ ربات فعال است!')

def main():
    print("🔍 بررسی توکن...")
    print(f"توکن: {BOT_TOKEN}")
    
    if not BOT_TOKEN:
        print("❌ توکن پیدا نشد!")
        return
    
    print("🤖 ساخت اپلیکیشن...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("🚀 شروع polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
