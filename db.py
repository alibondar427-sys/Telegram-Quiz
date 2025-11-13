# db.py -- helper برای اتصال و توابع دیتابیس
import aiosqlite
from pathlib import Path

DB_PATH = None

async def init(db_path: str):
    global DB_PATH
    DB_PATH = db_path
    path = Path(db_path)
    if not path.exists():
        async with aiosqlite.connect(DB_PATH) as db:
            schema = Path('schema.sql').read_text()
            await db.executescript(schema)
            await db.commit()

async def connect():
    return await aiosqlite.connect(DB_PATH)

async def get_published_quizzes():
    async with await connect() as db:
        cur = await db.execute("SELECT id, title, description, time_limit_minutes FROM quizzes WHERE is_published=1")
        rows = await cur.fetchall()
        return rows
