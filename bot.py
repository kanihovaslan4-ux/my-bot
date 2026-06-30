from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import database, asyncio, os

TOKEN = "8659732625:AAE8kUk3SEavTi98LmIkeYxiRZLNhwbEfeI"
CHANNEL_LINK = "https://t.me/gottec" # Ссылка на твой канал

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Мини-сервер
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
        [InlineKeyboardButton(text="📜 Правила и FAQ", callback_data="faq")]
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

@dp.callback_query(F.data == "withdraw")
async def withdraw_menu(call: types.CallbackQuery):
    _, count = await database.get_user_stats(call.from_user.id)
    if count * 5 < 15: return await call.answer("⚠️ Минимум 15 звезд!", show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{s} ⭐️", callback_data=f"w_{s}")] for s in [15, 25, 50, 100]] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]])
    await call.message.edit_text("<b>💰 ВЫБЕРИ СУММУ</b>\n━━━━━━━━━━━━━━━━━━━\n<i>Выплаты производятся ежедневно!</i>", parse_mode="HTML", reply_markup=kb)

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

@dp.callback_query(F.data == "faq")
async def faq(call: types.CallbackQuery):
    await call.message.edit_text(
        "<b>📜 КАК ЭТО РАБОТАЕТ?</b>\n━━━━━━━━━━━━━━━━━━━\n"
        "1. Забираешь реф-ссылку в разделе 'Пригласить друзей'.\n"
        "2. Раскидываешь её знакомым или в чаты.\n"
        "3. Получаешь 5 звезд за каждого!\n"
        "4. Заказываешь вывод и ждешь зачисления. 💸\n\n"
        "<i>Все честно и прозрачно!</i>", 
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]])
    )

async def main():
    await database.init_db()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


