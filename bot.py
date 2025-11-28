import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from db import init_db, create_or_get_user, update_user, get_user_stats
import random
from datetime import datetime

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

# سوالات دسته‌بندی شده
QUESTIONS = {
    "آسان": [
        {"q": "تهران پایتخت چه کشوری است؟", "a": "ایران", "hint": "کشوری در خاورمیانه"},
        {"q": "۲ + ۲ چند می‌شود؟", "a": "4", "hint": "حاصل جمع دو عدد یکسان"},
        {"q": "رنگ آسمان چیست؟", "a": "آبی", "hint": "رنگ دریا هم هست"},
    ],
    "متوسط": [
        {"q": "پایتخت فرانسه کجاست؟", "a": "پاریس", "hint": "شهر نورها"},
        {"q": "۵ × ۷ چند می‌شود؟", "a": "35", "hint": "حاصل ضرب ۵ در ۷"},
        {"q": "بزرگترین سیاره منظومه شمسی؟", "a": "مشتری", "hint": "سیاره گازی"},
    ]
}

# تایمر پاسخ‌گویی (ثانیه)
QUESTION_TIMEOUT = 30

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await create_or_get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("🎯 شروع آزمون", callback_data="start_quiz")],
        [InlineKeyboardButton("📊 آمار من", callback_data="my_stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎓 به ربات آزمون خوش آمدید!",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "start_quiz":
        keyboard = [
            [InlineKeyboardButton("😊 آسان", callback_data="level_آسان")],
            [InlineKeyboardButton("😐 متوسط", callback_data="level_متوسط")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📚 سطح سختی را انتخاب کنید:", reply_markup=reply_markup)
    
    elif data.startswith("level_"):
        level = data.split("_")[1]
        await start_quiz_session(user_id, level, context, query)
    
    elif data == "my_stats":
        await show_stats(user_id, query)

async def start_quiz_session(user_id, level, context, query):
    user_sessions[user_id] = {
        'level': level,
        'current_question': 0,
        'score': 0,
        'start_time': datetime.now(),
        'questions': random.sample(QUESTIONS[level], len(QUESTIONS[level]))
    }
    
    await query.edit_message_text(
        f"🎯 سطح {level} انتخاب شد!\n"
        f"⏰ زمان پاسخگویی: {QUESTION_TIMEOUT} ثانیه\n"
        f"📝 تعداد سوالات: {len(QUESTIONS[level])}\n\n"
        "آماده‌ای؟ /next را بفرست"
    )

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    if user_id not in user_sessions:
        await update.message.reply_text("❌ اول آزمون را شروع کنید: /start")
        return
    
    session = user_sessions[user_id]
    q_index = session['current_question']
    
    if q_index >= len(session['questions']):
        await finish_quiz(user_id, update, context)
        return
    
    question_data = session['questions'][q_index]
    
    await update.message.reply_text(
        f"📝 سوال {q_index + 1} از {len(session['questions'])}:\n"
        f"{question_data['q']}\n\n"
        f"⏰ زمان: {QUESTION_TIMEOUT} ثانیه"
    )

async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id not in user_sessions:
        return
    
    session = user_sessions[user_id]
    q_index = session['current_question']
    
    if q_index >= len(session['questions']):
        return
    
    question_data = session['questions'][q_index]
    correct_answer = question_data['a']
    
    if text.lower() == correct_answer.lower():
        session['score'] += 1
        await update.message.reply_text("✅ درست جواب دادی! 🎉")
    else:
        await update.message.reply_text(f"❌ اشتباه! پاسخ صحیح: {correct_answer}")
    
    session['current_question'] += 1
    
    if session['current_question'] >= len(session['questions']):
        await finish_quiz(user_id, update, context)
    else:
        await update.message.reply_text("برای سوال بعدی /next بفرست")

async def finish_quiz(user_id, update, context):
    session = user_sessions[user_id]
    total_time = (datetime.now() - session['start_time']).seconds
    
    await update_user(user_id, score=session['score'], level=session['level'])
    
    progress = "🟩" * session['score'] + "🟥" * (len(session['questions']) - session['score'])
    
    await update.message.reply_text(
        f"🎉 آزمون تمام شد!\n\n"
        f"📊 نتایج شما:\n"
        f"🏆 نمره: {session['score']} از {len(session['questions'])}\n"
        f"⏱️ زمان: {total_time} ثانیه\n"
        f"📈 نمودار: {progress}\n\n"
        f"برای شروع مجدد: /start"
    )
    
    del user_sessions[user_id]

async def show_stats(user_id, query):
    user = await get_user_stats(user_id)
    if user:
        await query.edit_message_text(
            f"📊 آمار شما:\n\n"
            f"🎯 مجموع آزمون‌ها: {user[3] or 0}\n"
            f"🏆 بالاترین نمره: {user[1] or 0}\n"
            f"📚 آخرین سطح: {user[4] or 'ندارد'}\n\n"
            f"برای آزمون جدید: /start"
        )

async def next_question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await ask_question(update, context, user_id)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("next", next_question_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer_handler))
    
    print("🤖 ربات آزمون در حال اجرا است...")
    app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
