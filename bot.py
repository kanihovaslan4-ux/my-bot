from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiohttp import web
import database, asyncio, os

TOKEN = "8659732625:AAFbCRywNhaX22_djBjYZYMFk57QpTFAURM"
CHANNEL_LINK = "https://t.me/gottec"
TELEGRAPH_URL = "https://telegra.ph/PravilaFAQ-06-30"
CHANNEL_ID = -1003903368955
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()

def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🔗 Пригласить друзей", callback_data="ref_link")],
        [InlineKeyboardButton(text="💰 Вывод средств", callback_data="withdraw")],
        [InlineKeyboardButton(text="🎟 Канал выплат", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="📜 Правила и FAQ", web_app=WebAppInfo(url=TELEGRAPH_URL))]
    ])

@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    await database.register_user_only(message.from_user.id, int(command.args) if command.args and command.args.isdigit() else None)
    await message.answer("👋 Привет! Добро пожаловать в систему.", reply_markup=get_main_kb())
    ref_id = await database.pay_reward(message.from_user.id)
    if ref_id:
        try: await bot.send_message(ref_id, "✅ Друг активировал бота! +5 звезд.")
        except: pass

@dp.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    reg, count = await database.get_user_stats(call.from_user.id)
    text = f"📊 ЛИЧНЫЙ КАБИНЕТ\n\nВ системе с: {reg}\nПриглашено: {count}\nБаланс: {count * 5} ⭐️"
    await call.message.edit_text(text, reply_markup=get_main_kb())

@dp.callback_query(F.data == "ref_link")
async def ref_link_handler(call: types.CallbackQuery):
    bot_info = await bot.get_me()
    text = (f"<b>🔗 Твоя ссылка:</b>\n<code>https://t.me/{bot_info.username}?start={call.from_user.id}</code>\n\n"
            "💎 <b>Как работает наша реферальная программа?</b>\n\n"
            "1. Скопируй ссылку.\n2. Приглашай друзей.\n3. Получай 5 звезд за каждого подписавшегося!\n\n"
            "⚠️ <b>Важно:</b> Награда начисляется только после подписки на все каналы.")
    await call.message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))

@dp.callback_query(F.data == "withdraw")
async def withdraw_menu(call: types.CallbackQuery):
    _, count = await database.get_user_stats(call.from_user.id)
    if count * 5 < 15: return await call.answer("⚠️ Минимум 15 звезд для вывода!", show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="15 ⭐️", callback_data="w_15")], [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]])
    await call.message.edit_text("💰 Выбери сумму для вывода:", reply_markup=kb)

@dp.callback_query(F.data.startswith("w_"))
@dp.callback_query(F.data.startswith("w_"))
async def request_withdraw(call: types.CallbackQuery):
    amount = int(call.data.split("_")[1])
    await database.create_withdrawal(call.from_user.id, amount)
    
    # Добавляем отправку уведомления в канал:
    await bot.send_message(CHANNEL_ID, f"🔔 Новая заявка!\n👤 Пользователь: @{call.from_user.username or call.from_user.id}\n💰 Сумма: {amount} звезд")
    
    await call.message.edit_text("✅ Заявка оформлена! Администратор скоро её проверит.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Назад", callback_data="profile")]]))


async def main():
    await database.init_db()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
@dp.message(F.text.startswith("/setbalance"))
async def admin_set_balance(message: types.Message):
    # Вставь сюда свой личный ID (его можно узнать, написав боту @userinfobot)
    ADMIN_ID = 7880039240 
    
    if message.from_user.id != ADMIN_ID:
        return # Игнорируем всех, кроме тебя
    
    try:
        amount = int(message.text.split()[1])
        await database.set_user_balance(message.from_user.id, amount)
        await message.answer(f"✅ Баланс успешно изменен на {amount} звезд!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
