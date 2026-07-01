import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

async def get_conn():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    conn = await get_conn()
    await conn.execute('''CREATE TABLE IF NOT EXISTS users 
                          (id BIGINT PRIMARY KEY, referrer_id BIGINT, reg_date TEXT)''')
    await conn.execute('''CREATE TABLE IF NOT EXISTS promocodes 
                          (code TEXT PRIMARY KEY, amount INTEGER, uses INTEGER)''')
    await conn.close()

async def register_user_only(user_id, referrer_id):
    conn = await get_conn()
    await conn.execute("INSERT INTO users (id, referrer_id, reg_date) VALUES ($1, $2, '01.07.2026') ON CONFLICT (id) DO NOTHING", user_id, referrer_id)
    await conn.close()

async def get_user_stats(user_id):
    conn = await get_conn()
    row = await conn.fetchrow("SELECT reg_date FROM users WHERE id = $1", user_id)
    count = await conn.fetchval("SELECT count(*) FROM users WHERE referrer_id = $1", user_id)
    await conn.close()
    return (row['reg_date'] if row else "01.07.2026"), (count if count else 0)

async def create_promo(code, amount, uses):
    conn = await get_conn()
    await conn.execute("INSERT INTO promocodes VALUES ($1, $2, $3)", code, amount, uses)
    await conn.close()

async def get_all_users():
    conn = await get_conn()
    rows = await conn.fetch("SELECT id FROM users")
    await conn.close()
    return [row['id'] for row in rows]
