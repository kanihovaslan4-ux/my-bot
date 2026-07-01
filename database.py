import asyncpg
import os

DB_URL = os.environ.get("DATABASE_URL")

async def init_db():
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            ref_id BIGINT,
            reg_date TEXT,
            count INTEGER DEFAULT 0,
            balance INTEGER DEFAULT 0
        )
    """)
    await conn.close()

async def register_user_only(user_id, ref_id):
    conn = await asyncpg.connect(DB_URL)
    # Пытаемся вставить юзера, если его еще нет
    await conn.execute("""
        INSERT INTO users (user_id, ref_id, reg_date) 
        VALUES ($1, $2, '01.07.2026') 
        ON CONFLICT (user_id) DO NOTHING
    """, user_id, ref_id)
    
    # Если это новый пользователь и у него есть реферер
    if ref_id:
        # Проверяем, не регистрировался ли он уже, чтобы не накручивали
        is_new = await conn.fetchval("SELECT count FROM users WHERE user_id = $1", user_id)
        if is_new is None:
            await conn.execute("UPDATE users SET count = count + 1, balance = balance + 5 WHERE user_id = $1", ref_id)
    await conn.close()

async def get_user_stats(user_id):
    conn = await asyncpg.connect(DB_URL)
    row = await conn.fetchrow("SELECT reg_date, count, balance FROM users WHERE user_id = $1", user_id)
    await conn.close()
    return row if row else ("01.07.2026", 0, 0)

async def withdraw_stars(user_id, amount):
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("UPDATE users SET balance = balance - $1 WHERE user_id = $2", amount, user_id)
    await conn.close()

