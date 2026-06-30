from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiohttp import web
import database, asyncio, os

TOKEN = "8659732625:AAE8kUk3SEavTi98LmIkeYxiRZLNhwbEfeI"
CHANNEL_LINK = "https://t.me/gottec" 
TELEGRAPH_URL = "https://telegra.ph/PravilaFAQ-06-30" 

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
    await message.answer(
        "<b>👋 Привет! Добро пожаловать в систему!</b>\n\n"
        "Мы — твой путь к первым заработанным звездам. 🚀\n"
        "Все прозрачно: приглашаешь, зарабатываешь, выводишь!\n\n"
        "<i>Используй меню ниже, чтобы начать:</i>", 
        parse_mode="HTML", reply_markup=get_main_kb()
    )
    ref_id = await database.pay_reward(message.from_user.id)
    if ref_id:
        try: await bot.send_message(ref_id, "✅ <b>Есть движение!</b>\nТвой друг активировал бота.\n💰 <i>+5 звезд на балансе!</i>", parse_mode="HTML")
        except: pass

@dp.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    reg, count = await database.get_user_stats(call.from_user.id)
    await call.message.edit_text(
        f"<b>📊 ЛИЧНЫЙ КАБИНЕТ</b>\n━━━━━━━━━━━━━━━━━━━\n"
        f"🗓 В системе с: <code>{reg}</code>\n"
        f"👥 Приглашено: <b>{count}</b>\n"
        f"💎 Баланс: <b>{count * 5}</b> ⭐️\n\n"
        f"<i>Копи копилку, чтобы сделать первый вывод!</i>", 
        parse_mode="HTML", reply_markup=get_main_kb()
    )

@dp.callback_query(F.data == "ref_link")
async def ref_link_handler(call: types.CallbackQuery):
    bot_info = await bot.get_me()
    text = (
        f"<b>🔗 ПАРТНЕРСКАЯ ПРОГРАММА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Твоя ссылка:\n<code>https://t.me/{bot_info.username}?start={call.from_user.id}</code>\n\n"
        f"💎 <b>За каждого друга — 5 звезд!</b>\n"
        f"Скопируй ссылку и делись ей в чатах и социальных сетях."
    )
    await call.message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))

@dp.callback_query(F.data == "withdraw")
async def withdraw_menu(call: types.CallbackQuery):
    _, count = await database.get_user_stats(call.from_user.id)
    balance = count * 5
    if balance < 15: return await call.answer("⚠️ Минимум 15 звезд для вывода!", show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{s} ⭐️", callback_data=f"w_{s}")] for s in [15, 25, 50, 100]] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]])
    await call.message.edit_text(f"<b>💰 ВЫБЕРИ СУММУ</b>\n━━━━━━━━━━━━━━━━━━━\nТвой баланс: {balance} ⭐️\n\n<i>Выплаты производятся ежедневно!</i>", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("w_"))
async def request_withdraw(call: types.CallbackQuery):
    amount = int(call.data.split("_")[1])
    await database.create_withdrawal(call.from_user.id, amount)
    await call.message.edit_text(
        f"✅ <b>Заявка оформлена!</b>\n\n"
        f"Твой запрос на <b>{amount} звезд</b> принят в обработку. 🕐\n"
        f"Следи за статусом в нашем канале выплат!\n\n"
        f"<i>Мы стараемся обрабатывать всё максимально быстро.</i>", 
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎟 Перейти в канал выплат", url=CHANNEL_LINK)], [InlineKeyboardButton(text="🏠 Назад", callback_data="profile")]])
    )

async def main():
    await database.init_db()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
