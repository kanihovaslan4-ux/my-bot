from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import database
import asyncio
import os

# Твой токен
TOKEN = "8659732625:AAE8kUk3SEavTi98LmIkeYxiRZLNhwbEfeI"
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Мини-сервер для поддержания активности на Render
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🔗 Пригласить друзей", callback_data="ref_link")],
        [InlineKeyboardButton(text="📜 Правила и FAQ", callback_data="faq")]
    ])

@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    args = command.args
    referrer_id = int(args) if args and args.isdigit() else None
    
    # Регистрация (безопасная)
    await database.register_user_only(message.from_user.id, referrer_id)
    
    # Красивое приветствие
    await message.answer(
        "<b>✨ ДОБРО ПОЖАЛОВАТЬ!</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Вы успешно активировали бота и прошли проверку.\n\n"
        "💎 <b>Используй кнопки ниже для управления профилем.</b>",
        parse_mode="HTML", reply_markup=get_main_kb()
    )
    
    # Начисление награды
    ref_id = await database.pay_reward(message.from_user.id)
    if ref_id:
        try: await bot.send_message(ref_id, "✅ <b>Ваш реферал активировал бота!</b>\n💰 <i>+5 звезд начислено!</i>", parse_mode="HTML")
        except: pass

@dp.callback_query(F.data == "profile")
async def profile_handler(call: types.CallbackQuery):
    reg, count = await database.get_user_stats(call.from_user.id)
    await call.message.edit_text(
        f"<b>📊 ЛИЧНЫЙ КАБИНЕТ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📅 Регистрация: <code>{reg}</code>\n"
        f"👥 Приглашено: <b>{count}</b> чел.\n"
        f"💎 Баланс: <b>{count * 5}</b> звезд\n"
        f"━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML", reply_markup=get_main_kb()
    )

@dp.callback_query(F.data == "ref_link")
async def ref_link_handler(call: types.CallbackQuery):
    bot_info = await bot.get_me()
    await call.message.edit_text(
        f"<b>🔗 ТВОЯ ССЫЛКА</b>\n━━━━━━━━━━━━━━━━━━━\n"
        f"<code>https://t.me/{bot_info.username}?start={call.from_user.id}</code>",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]])
    )

@dp.callback_query(F.data == "faq")
async def faq_handler(call: types.CallbackQuery):
    await call.message.edit_text(
        "<b>📜 ПРАВИЛА И FAQ</b>\n━━━━━━━━━━━━━━━━━━━\n"
        "1. Приглашай друзей по своей ссылке.\n"
        "2. Награда выдается, когда друг активирует бота.\n"
        "3. Вывод звезд доступен в профиле.",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]])
    )

async def main():
    await database.init_db()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

