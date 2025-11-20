import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from db import init_db, create_or_get_user, update_user

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

QUESTIONS = [
    {"q": "تهران پایتخت چه کشوری است؟", "a": "ایران"},
    {"q": "۲ + ۲ چند می‌شود؟", "a": "4"},
    {"q": "رنگ آسمان چیست؟", "a": "آبی"},
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await create_or_get_user(user_id)

    await update.message.reply_text(
        "سلام! برای شروع امتحان /quiz را بفرست."
    )

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

async def main():
    await init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
