# admin_utils.py -- توابع مدیریتی برای ایجاد/ویرایش کوییز و سوال
from db import connect

async def create_quiz(title: str, description: str, created_by: int, time_limit_minutes):
    async with await connect() as db:
        cur = await db.execute(
            "INSERT INTO quizzes(title, description, created_by, time_limit_minutes) VALUES (?, ?, ?, ?)",
            (title, description, created_by, time_limit_minutes)
        )
        await db.commit()
        return cur.lastrowid

async def add_question(quiz_id: int, text: str, q_type: str, points: int = 1, time_limit_seconds: int = None, position: int = 0):
    async with await connect() as db:
        cur = await db.execute(
            "INSERT INTO questions(quiz_id, text, q_type, points, time_limit_seconds, position) VALUES (?, ?, ?, ?, ?, ?)",
            (quiz_id, text, q_type, points, time_limit_seconds, position)
        )
        await db.commit()
        return cur.lastrowid

async def add_choice(question_id: int, text: str, is_correct: bool = False, position: int = 0):
    async with await connect() as db:
        cur = await db.execute(
            "INSERT INTO choices(question_id, text, is_correct, position) VALUES (?, ?, ?, ?)",
            (question_id, text, int(is_correct), position)
        )
        await db.commit()
        return cur.lastrowid
