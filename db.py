import aiosqlite
import os

DB_PATH = "quiz_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                score INTEGER DEFAULT 0,
                current_question INTEGER DEFAULT 0,
                total_quizzes INTEGER DEFAULT 0,
                level TEXT DEFAULT 'آسان'
            )
        ''')
        await db.commit()

async def create_or_get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        await db.commit()
        
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = await cursor.fetchone()
        await cursor.close()
        return user

async def update_user(user_id, score=None, question=None, level=None):
    async with aiosqlite.connect(DB_PATH) as db:
        updates = []
        params = []
        
        if score is not None:
            updates.append("score = ?")
            params.append(score)
        
        if question is not None:
            updates.append("current_question = ?")
            params.append(question)
            
        if level is not None:
            updates.append("level = ?")
            params.append(level)
            
        if updates:
            params.append(user_id)
            await db.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?",
                params
            )
            await db.commit()

async def get_user_stats(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = await cursor.fetchone()
        await cursor.close()
        return user
