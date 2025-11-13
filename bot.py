# bot.py
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import aiosqlite
from db import init, connect
import admin_utils
from datetime import datetime, timedelta

load_dotenv()
TOKEN = os.getenv('TG_BOT_TOKEN')
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS','').split(',') if x.strip()]
DB_PATH = os.getenv('DATABASE_PATH','./quiz_bot.db')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class NewQuiz(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_time_limit = State()

class NewQuestion(StatesGroup):
    waiting_quiz_id = State()
    waiting_q_type = State()
    waiting_text = State()
    waiting_points = State()
    waiting_time_limit = State()
    waiting_choices = State()

TEMP_CHOICES = {}

async def is_admin(user_id: int):
    return user_id in ADMIN_IDS

async def on_startup(dp):
    await init(DB_PATH)
    logging.info("DB initialized")

@dp.message_handler(commands=['start'])
async def cmd_start(msg: types.Message):
    await msg.answer("سلام. به ربات آزمون خوش آمدی. برای دیدن آزمون‌ها /take را بزن.")

@dp.message_handler(commands=['help'])
async def cmd_help(msg: types.Message):
    await msg.answer("دستورات: /take برای شروع آزمون. ادمین‌ها: /newquiz, /newquestion, /publish <quiz_id>")

@dp.message_handler(commands=['take'])
async def cmd_take(msg: types.Message):
    async with await connect() as db:
        cur = await db.execute("SELECT id, title, description FROM quizzes WHERE is_published=1")
        rows = await cur.fetchall()
    if not rows:
        await msg.answer("هیچ آزمون فعالی وجود ندارد.")
        return
    kb = InlineKeyboardMarkup()
    for r in rows:
        kb.add(InlineKeyboardButton(r[1], callback_data=f"startq:{r[0]}"))
    await msg.answer("آزمون‌های فعال:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('startq:'))
async def cb_start_quiz(call: types.CallbackQuery):
    quiz_id = int(call.data.split(':')[1])
    user_id = call.from_user.id
    async with await connect() as db:
        cur = await db.execute("SELECT id FROM sessions WHERE user_id=? AND quiz_id=? AND status='in_progress'", (user_id, quiz_id))
        exist = await cur.fetchone()
        if exist:
            await bot.answer_callback_query(call.id, "شما یک آزمون باز از این کوییز دارید. ادامه آن را انجام دهید.")
            await bot.send_message(user_id, "شما یک آزمون باز دارید. برای ادامه /resume را بزنید.")
            return
        cur = await db.execute("SELECT time_limit_minutes FROM quizzes WHERE id=?", (quiz_id,))
        row = await cur.fetchone()
        expires = None
        if row and row[0]:
            expires = (datetime.utcnow() + timedelta(minutes=row[0])).isoformat()
        c = await db.execute("INSERT INTO sessions(user_id, quiz_id, expires_at) VALUES (?, ?, ?)", (user_id, quiz_id, expires))
        await db.commit()
        session_id = c.lastrowid
    await bot.answer_callback_query(call.id, "آزمون شروع شد")
    await send_next_question(user_id, session_id)

async def send_next_question(user_id: int, session_id: int):
    async with await connect() as db:
        cur = await db.execute("SELECT quiz_id, current_question_index, expires_at FROM sessions WHERE id=?", (session_id,))
        row = await cur.fetchone()
        if not row:
            await bot.send_message(user_id, "جلسه پیدا نشد.")
            return
        quiz_id, idx, expires_at = row
        if expires_at:
            if datetime.utcnow() > datetime.fromisoformat(expires_at):
                await db.execute("UPDATE sessions SET status='timed_out', finished_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
                await db.commit()
                await bot.send_message(user_id, "زمان آزمون تمام شد.")
                return
        cur = await db.execute("SELECT id, text, q_type, points, time_limit_seconds FROM questions WHERE quiz_id=? ORDER BY position, id", (quiz_id,))
        questions = await cur.fetchall()
        if idx >= len(questions):
            cur = await db.execute("SELECT score FROM sessions WHERE id=?", (session_id,))
            score = (await cur.fetchone())[0]
            await db.execute("UPDATE sessions SET status='finished', finished_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
            await db.commit()
            await bot.send_message(user_id, f"آزمون به پایان رسید. نمرهٔ شما: {score}")
            return
        q = questions[idx]
        qid, qtext, qtype, qpoints, qtime = q
        if qtype == 'mcq' or qtype == 'truefalse':
            cur = await db.execute("SELECT id, text FROM choices WHERE question_id=? ORDER BY position, id", (qid,))
            choices = await cur.fetchall()
            import random
            choices = list(choices)
            random.shuffle(choices)
            kb = InlineKeyboardMarkup()
            for c in choices:
                kb.add(InlineKeyboardButton(c[1], callback_data=f"answer:{session_id}:{qid}:{c[0]}"))
            await bot.send_message(user_id, f"سوال ({idx+1}):\n{qtext}")
            await bot.send_message(user_id, "گزینه‌ها:", reply_markup=kb)
        elif qtype == 'text':
            await bot.send_message(user_id, f"سوال ({idx+1}):\n{qtext}\n(لطفاً پاسخ خود را ارسال کنید)")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('answer:'))
async def cb_answer(call: types.CallbackQuery):
    _, session_id_s, question_id_s, choice_id_s = call.data.split(':')
    session_id = int(session_id_s); question_id = int(question_id_s); choice_id = int(choice_id_s)
    user_id = call.from_user.id
    async with await connect() as db:
        cur = await db.execute("SELECT quiz_id, current_question_index, expires_at FROM sessions WHERE id=?", (session_id,))
        row = await cur.fetchone()
        if not row:
            await bot.answer_callback_query(call.id, "سشن معتبر نیست.")
            return
        quiz_id, idx, expires_at = row
        if expires_at and datetime.utcnow() > datetime.fromisoformat(expires_at):
            await db.execute("UPDATE sessions SET status='timed_out', finished_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
            await db.commit()
            await bot.answer_callback_query(call.id, "زمان آزمون گذشته است.")
            return
        cur = await db.execute("SELECT is_correct FROM choices WHERE id=?", (choice_id,))
        row = await cur.fetchone()
        is_correct = bool(row[0]) if row else False
        points = 1 if is_correct else 0
        await db.execute(
            "INSERT INTO answers(session_id, question_id, chosen_choice_id, is_correct, points_awarded) VALUES (?, ?, ?, ?, ?)",
            (session_id, question_id, choice_id, int(is_correct), points)
        )
        new_index = idx + 1
        cur = await db.execute("SELECT score FROM sessions WHERE id=?", (session_id,))
        old_score = (await cur.fetchone())[0]
        new_score = old_score + points
        await db.execute("UPDATE sessions SET current_question_index=?, score=? WHERE id=?", (new_index, new_score, session_id))
        await db.commit()
    await bot.answer_callback_query(call.id, f"پاسخ ثبت شد. {'صحیح' if is_correct else 'غلط'}.")
    await send_next_question(user_id, session_id)

@dp.message_handler(lambda m: m.text and not m.text.startswith('/'))
async def handle_text_answer(msg: types.Message):
    user_id = msg.from_user.id
    async with await connect() as db:
        cur = await db.execute("SELECT id, quiz_id, current_question_index, expires_at FROM sessions WHERE user_id=? AND status='in_progress'", (user_id,))
        row = await cur.fetchone()
        if not row:
            return
        session_id, quiz_id, idx, expires_at = row
        if expires_at and datetime.utcnow() > datetime.fromisoformat(expires_at):
            await db.execute("UPDATE sessions SET status='timed_out', finished_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
            await db.commit()
            await msg.answer("زمان آزمون تمام شد.")
            return
        cur = await db.execute("SELECT id, text, q_type, points FROM questions WHERE quiz_id=? ORDER BY position, id LIMIT 1 OFFSET ?", (quiz_id, idx))
        q = await cur.fetchone()
        if not q:
            return
        qid, qtext, qtype, qpoints = q
        if qtype != 'text':
            return
        await db.execute("INSERT INTO answers(session_id, question_id, given_text, is_correct, points_awarded) VALUES (?, ?, ?, ?, ?)",
                         (session_id, qid, msg.text, 0, 0))
        new_index = idx + 1
        await db.execute("UPDATE sessions SET current_question_index=? WHERE id=?", (new_index, session_id))
        await db.commit()
    await msg.answer("پاسخ شما ثبت شد. این سوال نیاز به تصحیح دستی دارد.")
    await send_next_question(user_id, session_id)

@dp.message_handler(commands=['newquiz'])
async def cmd_newquiz(msg: types.Message):
    if not await is_admin(msg.from_user.id):
        await msg.reply('فقط ادمین‌ها می‌توانند اینکار را انجام دهند')
        return
    await NewQuiz.waiting_title.set()
    await msg.reply('عنوان آزمون را ارسال کنید:')

@dp.message_handler(state=NewQuiz.waiting_title)
async def process_quiz_title(msg: types.Message, state: FSMContext):
    await state.update_data(title=msg.text)
    await NewQuiz.next()
    await msg.reply('توضیح (یا "-" برای خالی):')

@dp.message_handler(state=NewQuiz.waiting_description)
async def process_quiz_desc(msg: types.Message, state: FSMContext):
    desc = None if msg.text.strip() == '-' else msg.text
    await state.update_data(description=desc)
    await NewQuiz.next()
    await msg.reply('زمان کل آزمون به دقیقه (یا "-" برای نامحدود):')

@dp.message_handler(state=NewQuiz.waiting_time_limit)
async def process_quiz_time(msg: types.Message, state: FSMContext):
    text = msg.text.strip()
    t = None
    if text != '-':
        try:
            t = int(text)
        except:
            await msg.reply('مقدار نامعتبر. عدد دقیقه یا "-" را ارسال کن.')
            return
    data = await state.get_data()
    quiz_id = await admin_utils.create_quiz(data['title'], data['description'], msg.from_user.id, t)
    await msg.reply(f'کوییز ساخته شد. id = {quiz_id}\nحالا برای اضافه کردن سوال /newquestion را بزن.')
    await state.finish()

@dp.message_handler(commands=['newquestion'])
async def cmd_newquestion(msg: types.Message):
    if not await is_admin(msg.from_user.id):
        await msg.reply('فقط ادمین‌ها')
        return
    await NewQuestion.waiting_quiz_id.set()
    await msg.reply('آی‌دی کوییز را ارسال کن:')

@dp.message_handler(state=NewQuestion.waiting_quiz_id)
async def proc_q_quizid(msg: types.Message, state: FSMContext):
    try:
        qid = int(msg.text.strip())
    except:
        await msg.reply('آی‌دی نامعتبر.')
        return
    await state.update_data(quiz_id=qid)
    await NewQuestion.next()
    await msg.reply('نوع سوال؟ یکی از: mcq, text, truefalse')

@dp.message_handler(state=NewQuestion.waiting_q_type)
async def proc_q_type(msg: types.Message, state: FSMContext):
    qt = msg.text.strip().lower()
    if qt not in ('mcq','text','truefalse'):
        await msg.reply('نوع نامعتبر. یکی از: mcq, text, truefalse')
        return
    await state.update_data(q_type=qt)
    await NewQuestion.next()
    await msg.reply('متن سوال را ارسال کن:')

@dp.message_handler(state=NewQuestion.waiting_text)
async def proc_q_text(msg: types.Message, state: FSMContext):
    await state.update_data(text=msg.text)
    await NewQuestion.next()
    await msg.reply('نمرهٔ سوال (پیش‌فرض 1):')

@dp.message_handler(state=NewQuestion.waiting_points)
async def proc_q_points(msg: types.Message, state: FSMContext):
    try:
        p = int(msg.text.strip())
    except:
        p = 1
    await state.update_data(points=p)
    await NewQuestion.next()
    await msg.reply('زمان سوال به ثانیه (یا "-" برای نداشتن):')

@dp.message_handler(state=NewQuestion.waiting_time_limit)
async def proc_q_time(msg: types.Message, state: FSMContext):
    text = msg.text.strip()
    t = None
    if text != '-':
        try:
            t = int(text)
        except:
            await msg.reply('مقدار نامعتبر. عدد ثانیه یا "-"')
            return
    await state.update_data(time_limit_seconds=t)
    data = await state.get_data()
    qid = await admin_utils.add_question(data['quiz_id'], data['text'], data['q_type'], data['points'], t)
    await msg.reply(f'سوال اضافه شد. id = {qid}')
    if data['q_type'] == 'mcq':
        TEMP_CHOICES[qid] = []
        await msg.reply('حالا گزینه‌ها را یکی‌یکی بفرست. وقتی تمام شد /done را بزن. ارسال هر گزینه با فرمت: متن | 1 یا 0 (1 اگر درست است)\nمثال:\nگزینهٔ اول | 0')
        await NewQuestion.next()
    else:
        await msg.reply('سوال متنی/تشریحی اضافه شد.')
        await state.finish()

@dp.message_handler(commands=['done'], state=NewQuestion.waiting_choices)
async def proc_choices_done(msg: types.Message, state: FSMContext):
    for qid, choices in list(TEMP_CHOICES.items()):
        if choices:
            for pos, (text, is_correct) in enumerate(choices):
                await admin_utils.add_choice(qid, text, bool(is_correct), pos)
            await msg.reply(f'گزینه‌ها برای سوال {qid} ذخیره شد.')
            del TEMP_CHOICES[qid]
            await state.finish()
            return
    await msg.reply('هیچ گزینه‌ای برای ذخیره وجود ندارد.')

@dp.message_handler(state=NewQuestion.waiting_choices)
async def proc_choice_line(msg: types.Message, state: FSMContext):
    parts = msg.text.split('|')
    if len(parts) < 2:
        await msg.reply('فرمت نادرست. از "متن | 1" استفاده کن')
        return
    text = parts[0].strip()
    flag = parts[1].strip()
    is_correct = 1 if flag in ('1','true','True') else 0
    if not TEMP_CHOICES:
        await msg.reply('خطا: سوال مقصد پیدا نشد.')
        return
    qid = list(TEMP_CHOICES.keys())[-1]
    TEMP_CHOICES[qid].append((text, is_correct))
    await msg.reply('گزینه ثبت شد. /done وقتی تمام شد')

@dp.message_handler(commands=['publish'])
async def cmd_publish(msg: types.Message):
    if not await is_admin(msg.from_user.id):
        await msg.reply('فقط ادمین‌ها')
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.reply('فرمت: /publish <quiz_id>')
        return
    try:
        qid = int(parts[1])
    except:
        await msg.reply('id نامعتبر')
        return
    async with await connect() as db:
        await db.execute("UPDATE quizzes SET is_published=1 WHERE id=?", (qid,))
        await db.commit()
    await msg.reply(f'کوییز {qid} منتشر شد.')

@dp.message_handler(commands=['resume'])
async def cmd_resume(msg: types.Message):
    user_id = msg.from_user.id
    async with await connect() as db:
        cur = await db.execute("SELECT id FROM sessions WHERE user_id=? AND status='in_progress'", (user_id,))
        r = await cur.fetchone()
        if not r:
            await msg.reply('آزمون باز پیدا نشد.')
            return
        session_id = r[0]
    await send_next_question(user_id, session_id)

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup)
