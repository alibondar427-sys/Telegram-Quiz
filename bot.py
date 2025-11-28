import os
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from db import init_db, create_or_get_user, update_user
from flask import Flask
from threading import Thread

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

# سرور Flask برای باز کردن پورت
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running!"

QUESTIONS = [
    {"q": "تهران پایتخت چه کشوری است؟", "a": "ایران"},
    {"q": "۲ + ۲ چند می‌شود؟", "a": "4"},
    {"q": "رنگ آسمان چیست؟", "a": "آبی"},
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await create_or_get_user(user_id)
    await update.message.reply_text("سلام! برای شروع امتحان /quiz را بفرست.")

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await create_or_get_user(user_id)
    q_index = user[2]

    if q_index >= len(QUESTIONS):
        await update.message.reply_text("امتحان تمام شد! /score را بزن تا نمرت را ببینی.")
        return

    question = QUESTIONS[q_index]["q"]
    await update.message.reply_text(f"سؤال {q_index+1}:\n{question}")

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user = await create_or_get_user(user_id)
    q_index = user[2]

    if q_index >= len(QUESTIONS):
        await update.message.reply_text("امتحان تمام شده. /score را بزن.")
        return

    correct = QUESTIONS[q_index]["a"]
    if text.lower() == correct.lower():
        await update_user(user_id, score=user[1] + 1)
        await update.message.reply_text("درست بود!")
    else:
        await update.message.reply_text(f"غلط بود. جواب درست: {correct}")

    await update_user(user_id, question=q_index + 1)
    await quiz(update, context)

async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await create_or_get_user(user_id)
    await update.message.reply_text(f"نمره شما: {user[1]} از {len(QUESTIONS)}")

async def run_bot():
    """اجرای ربات تلگرام"""
    await init_db()
    
    bot_app = Application.builder().token(BOT_TOKEN).build()
    
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("quiz", quiz))
    bot_app.add_handler(CommandHandler("score", score))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))
    
    print("🤖 ربات تلگرام در حال اجرا است...")
    await bot_app.run_polling()

def run_flask():
    """اجرای سرور Flask برای پورت"""
    print("🌐 سرور Flask در حال اجرا روی پورت 10000...")
    app.run(host='0.0.0.0', port=10000)

def main():
    if not BOT_TOKEN:
        print("❌ توکن پیدا نشد!")
        return
    
    # اجرای ربات در thread جداگانه
    bot_thread = Thread(target=lambda: asyncio.run(run_bot()))
    bot_thread.daemon = True
    bot_thread.start()
    
    # اجرای Flask
    run_flask()

if __name__ == "__main__":
    main()
