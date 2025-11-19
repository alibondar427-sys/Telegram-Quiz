import aiosqlite

DB_NAME = "quiz.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                score INTEGER DEFAULT 0,
                current_question INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def create_or_get_user(user_id):
    user = await get_user(user_id)
    if user:
        return user
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO users (user_id, score, current_question) VALUES (?, 0, 0)", (user_id,))
        await db.commit()
    return await get_user(user_id)

async def update_user(user_id, score=None, question=None):
    async with aiosqlite.connect(DB_NAME) as db:
        if score is not None:
            await db.execute("UPDATE users SET score = ? WHERE user_id = ?", (score, user_id))
        if question is not None:
            await db.execute("UPDATE users SET current_question = ? WHERE user_id = ?", (question, user_id))
        await db.commit()
