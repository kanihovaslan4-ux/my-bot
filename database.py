import aiosqlite

async def init_db():
    async with aiosqlite.connect("bot_data.db") as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
                          (id INTEGER PRIMARY KEY, referrer_id INTEGER, reg_date TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS payouts 
                          (referrer_id INTEGER, user_id INTEGER)''')
        await db.commit()

async def register_user_only(user_id, referrer_id):
    from datetime import datetime
    async with aiosqlite.connect("bot_data.db") as db:
        date = datetime.now().strftime("%d.%m.%Y")
        await db.execute("INSERT OR IGNORE INTO users (id, referrer_id, reg_date) VALUES (?, ?, ?)", 
                         (user_id, referrer_id, date))
        await db.commit()

async def pay_reward(user_id):
    async with aiosqlite.connect("bot_data.db") as db:
        cursor = await db.execute("SELECT referrer_id FROM users WHERE id = ? AND referrer_id IS NOT NULL", (user_id,))
        row = await cursor.fetchone()
        
        if row:
            referrer_id = row[0]
            cursor_pay = await db.execute("SELECT * FROM payouts WHERE user_id = ?", (user_id,))
            if not await cursor_pay.fetchone():
                await db.execute("INSERT INTO payouts (referrer_id, user_id) VALUES (?, ?)", (referrer_id, user_id))
                await db.commit()
                return referrer_id
        return None

async def get_user_stats(user_id):
    async with aiosqlite.connect("bot_data.db") as db:
        cursor = await db.execute("SELECT reg_date FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        cursor_ref = await db.execute("SELECT count(*) FROM payouts WHERE referrer_id = ?", (user_id,))
        ref_count = await cursor_ref.fetchone()
        return (row[0] if row else "Нет данных"), (ref_count[0] if ref_count else 0)
