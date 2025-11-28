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
    ],
    "سخت": [
        {"q": "معادله x² - 5x + 6 = 0 را حل کنید", "a": "2,3", "hint": "از روش تجزیه استفاده کن"},
        {"q": "پایتخت استرالیا؟", "a": "کانبرا", "hint": "سیدنی نیست!"},
        {"q": "سال تأسیس سازمان ملل؟", "a": "1945", "hint": "بعد از جنگ جهانی دوم"},
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
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎓 به ربات آزمون پیشرفته خوش آمدید!\n"
        "لطفاً یک گزینه را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "start_quiz":
        # انتخاب سطح سختی
        keyboard = [
            [InlineKeyboardButton("😊 آسان", callback_data="level_آسان")],
            [InlineKeyboardButton("😐 متوسط", callback_data="level_متوسط")],
            [InlineKeyboardButton("😰 سخت", callback_data="level_سخت")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📚 لطفاً سطح سختی را انتخاب کنید:", reply_markup=reply_markup)
    
    elif data.startswith("level_"):
        level = data.split("_")[1]
        await start_quiz_session(user_id, level, context, query)
    
    elif data == "my_stats":
        await show_stats(user_id, query)
    
    elif data == "help":
        await show_help(query)

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
        f"⏰ زمان پاسخگویی: {QUESTION_TIMEOUT} ثانیه برای هر سوال\n"
        f"📝 تعداد سوالات: {len(QUESTIONS[level])}\n\n"
        "آماده‌ای؟ /next را بفرست یا کلیک کن:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ سوال بعدی", callback_data="next_question")]])
    )

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    if user_id not in user_sessions:
        await update.message.reply_text("❌ لطفاً اول آزمون را شروع کنید: /start")
        return
    
    session = user_sessions[user_id]
    level = session['level']
    q_index = session['current_question']
    
    if q_index >= len(session['questions']):
        await finish_quiz(user_id, update, context)
        return
    
    question_data = session['questions'][q_index]
    
    # دکمه‌های راهنما
    keyboard = [
        [InlineKeyboardButton("💡 راهنما", callback_data=f"hint_{q_index}")],
        [InlineKeyboardButton("⏩ رد کردن", callback_data=f"skip_{q_index}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = await update.message.reply_text(
        f"📝 سوال {q_index + 1} از {len(session['questions']} (سطح {level}):\n"
        f"{question_data['q']}\n\n"
        f"⏰ زمان: {QUESTION_TIMEOUT} ثانیه",
        reply_markup=reply_markup
    )
    
    # تایمر خودکار
    context.job_queue.run_once(timeout_question, QUESTION_TIMEOUT, 
                              data=(user_id, message.message_id, q_index))

async def timeout_question(context):
    user_id, message_id, q_index = context.job.data
    if user_id in user_sessions and user_sessions[user_id]['current_question'] == q_index:
        session = user_sessions[user_id]
        question_data = session['questions'][q_index]
        
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=f"⏰ زمان تمام شد!\n\n{session['questions'][q_index]['q']}\n✅ پاسخ صحیح: {question_data['a']}"
        )
        
        session['current_question'] += 1
        await send_next_prompt(context.bot, user_id)

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
    await send_next_prompt(context.bot, user_id)

async def send_next_prompt(bot, user_id):
    session = user_sessions[user_id]
    
    if session['current_question'] >= len(session['questions']):
        await finish_quiz(user_id, None, None, bot)
    else:
        keyboard = [[InlineKeyboardButton("➡️ سوال بعدی", callback_data="next_question")]]
        await bot.send_message(
            user_id,
            "آماده برای سوال بعدی؟",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def finish_quiz(user_id, update, context, bot=None):
    if not bot:
        bot = context.bot
    
    session = user_sessions[user_id]
    total_time = (datetime.now() - session['start_time']).seconds
    level = session['level']
    
    # ذخیره نتایج در دیتابیس
    await update_user(user_id, score=session['score'], level=level)
    
    # نمودار پیشرفت ساده
    progress = "🟩" * session['score'] + "🟥" * (len(session['questions']) - session['score'])
    
    await bot.send_message(
        user_id,
        f"🎉 آزمون تمام شد!\n\n"
        f"📊 نتایج شما (سطح {level}):\n"
        f"🏆 نمره: {session['score']} از {len(session['questions'])}\n"
        f"⏱️ زمان: {total_time} ثانیه\n"
        f"📈 نمودار: {progress}\n\n"
        f"برای شروع مجدد: /start"
    )
    
    # حذف سشن
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
    else:
        await query.edit_message_text("❌ اطلاعاتی یافت نشد. اول یک آزمون بده!")

async def show_help(query):
    help_text = """
📖 راهنمای ربات آزمون:

🎯 **دستورات اصلی:**
/start - شروع ربات
/stats - نمایش آمار
/help - راهنما

📚 **سطح‌های سختی:**
😊 آسان - سوالات عمومی
😐 متوسط - سوالات متوسط
😰 سخت - سوالات چالشی

⏰ **تایمر:**
هر سوال ۳۰ ثانیه زمان داره

💡 **امکانات:**
- راهنمای سوالات
- رد کردن سوال
- نمودار پیشرفت
- آمار کامل

برای شروع: /start
    """
    await query.edit_message_text(help_text)

async def next_question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await ask_question(update, context, user_id)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("next", next_question_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer_handler))
    
    print("🤖 ربات آزمون پیشرفته در حال اجرا است...")
    app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
