import os
import sys
from telegram.ext import Application, CommandHandler

print("🎯 اسکریپت شروع شد...")
print(f"📁 مسیر جاری: {os.getcwd()}")
print(f"📋 فایل‌ها: {os.listdir('.')}")

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
print(f"🔍 توکن: {BOT_TOKEN}")

if not BOT_TOKEN:
    print("❌ توکن پیدا نشد!")
    sys.exit(1)

async def start(update, context):
    print(f"📨 دریافت /start از کاربر: {update.effective_user.id}")
    await update.message.reply_text('✅ ربات فعال است!')

print("🤖 ساخت اپلیکیشن...")
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))

print("🚀 شروع polling...")
app.run_polling()
print("✅ ربات در حال اجراست!")
