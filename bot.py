import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- НАСТРОЙКИ ---
API_TOKEN = '8659732625:AAGXvNoEdrw4Wb_hwEwvNRXWTxI1O8pvyck'
ADMIN_ID = 7880039240  # Твой ID для получения заявок
CHANNELS = ["@channel1", "@channel2"] # Список каналов
REWARD = 4 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БД ---
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, referrer INTEGER, balance INTEGER DEFAULT 0)')
conn.commit()

async def is_subscribed(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except: return False
    return True

# --- КЛАВИАТУРА ---
def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Моя ссылка", callback_data="get_link")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="💸 Вывод средств", callback_data="withdraw_menu")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    args = message.text.split()
    user_id = message.from_user.id
    
    # Регистрация
    cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    if not cursor.fetchone():
        referrer = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        cursor.execute('INSERT INTO users (id, referrer) VALUES (?, ?)', (user_id, referrer))
        conn.commit()
        
        # Начисление
        if referrer and referrer != user_id:
            cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (REWARD, referrer))
            conn.commit()
            try: await bot.send_message(referrer, f"🎉 У вас новый реферал! +{REWARD} звезд.")
            except: pass

    await message.answer("👋 Добро пожаловать!\nПриглашай друзей и зарабатывай звезды.", reply_markup=main_kb())

@dp.callback_query(F.data == "get_link")
async def get_link(call: types.CallbackQuery):
    await call.message.answer(f"Твоя ссылка: https://t.me/{(await bot.get_me()).username}?start={call.from_user.id}")

@dp.callback_query(F.data == "balance")
async def balance(call: types.CallbackQuery):
    cursor.execute('SELECT balance FROM users WHERE id = ?', (call.from_user.id,))
    bal = cursor.fetchone()[0]
    await call.message.answer(f"💰 Твой баланс: {bal} звезд.")

@dp.callback_query(F.data == "withdraw_menu")
async def withdraw_menu(call: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="15", callback_data="w_15"), InlineKeyboardButton(text="25", callback_data="w_25")],
        [InlineKeyboardButton(text="50", callback_data="w_50"), InlineKeyboardButton(text="100", callback_data="w_100")]
    ])
    await call.message.answer("Выберите сумму для вывода:", reply_markup=kb)

@dp.callback_query(F.data.startswith("w_"))
async def withdraw_request(call: types.CallbackQuery):
    amount = int(call.data.split("_")[1])
    cursor.execute('SELECT balance FROM users WHERE id = ?', (call.from_user.id,))
    bal = cursor.fetchone()[0]
    
    if bal >= amount:
        cursor.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, call.from_user.id))
        conn.commit()
        await bot.send_message(ADMIN_ID, f"🔔 Новая заявка!\nUser: {call.from_user.id}\nСумма: {amount}")
        await call.message.answer(f"✅ Заявка на {amount} звезд принята!")
    else:
        await call.message.answer("❌ Недостаточно средств.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
