from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiohttp import web
import database, asyncio, os

TOKEN = "8659732625:AAFbCRywNhaX22_djBjYZYMFk57QpTFAURM"
CHANNEL_LINK = "https://t.me/gottec"
TELEGRAPH_URL = "https://telegra.ph/PravilaFAQ-06-30"
ADMIN_ID = 7880039240 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def start_web_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()

# --- КЛАВИАТУРА ---
def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🔗 Пригласить друзей", callback_data="ref_link")],
        [InlineKeyboardButton(text="💰 Вывод средств", callback_data="withdraw")],
        [InlineKeyboardButton(text="🎟 Канал выплат", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="📜 Правила и FAQ", web_app=WebAppInfo(url=TELEGRAPH_URL))]
    ])

# --- КОМАНДЫ И ОБРАБОТЧИКИ ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    await database.register_user_only(message.from_user.id, int(command.args) if command.args and command.args.isdigit() else None)
    await message.answer("👋 Привет! Добро пожаловать в систему.", reply_markup=get_main_kb())

@dp.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    reg, count = await database.get_user_stats(call.from_user.id)
    text = (f"💎 <b>ЛИЧНЫЙ КАБИНЕТ</b> 💎\n\n"
            f"👤 <b>ID:</b> <code>{call.from_user.id}</code>\n"
            f"📅 <b>В системе с:</b> {reg}\n"
            f"👥 <b>Приглашено:</b> {count}\n\n"
            f"⭐️ <b>Твой баланс:</b> {count * 5} звезд")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_kb())

@dp.callback_query(F.data == "ref_link")
async def ref_link_handler(call: types.CallbackQuery):
    bot_info = await bot.get_me()
    text = (f"<b>🔗 Твоя ссылка:</b>\n<code>https://t.me/{bot_info.username}?start={call.from_user.id}</code>\n\n"
            "💎 <b>Приглашай друзей и получай 5 звезд за каждого!</b>")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))

# --- АДМИН-ПАНЕЛЬ ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🛠 <b>Админ-панель:</b>\n\n/promo [код] [сумма] [использования]\n/send [текст] - рассылка")

@dp.message(F.text.startswith("/promo"))
async def add_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 4: return await message.answer("Ошибка! Формат: /promo [код] [сумма] [использования]")
    await database.create_promo(args[1], int(args[2]), int(args[3]))
    await message.answer(f"✅ Промокод {args[1]} на {args[2]} звезд создан!")

@dp.message(F.text.startswith("/send"))
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/send ", "")
    users = await database.get_all_users()
    for user_id in users:
        try: await bot.send_message(user_id, text)
        except: continue
    await message.answer("✅ Рассылка завершена.")

# --- ЗАПУСК ---
async def main():
    await database.init_db()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


