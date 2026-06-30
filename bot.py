from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import database
import asyncio

bot = Bot(token="8659732625:AAGXvNoEdrw4Wb_hwEwvNRXWTxI1O8pvyck")
dp = Dispatcher()

# --- ВЕБ-ЗАГЛУШКА ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
# -------------------------------

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
    
    await database.register_user_only(message.from_user.id, referrer_id)
    
    await message.answer(
        "✨ **Добро пожаловать в систему!** ✨\n\n"
        "Ты успешно активировал бота и прошел все проверки безопасности. "
        "Теперь ты полноценный участник нашей системы заработка. 🚀\n\n"
        "💎 **Используй кнопки ниже, чтобы управлять профилем и следить за балансом.**",
        reply_markup=get_main_kb()
    )
    
    ref_id = await database.pay_reward(message.from_user.id)
    if ref_id:
        try:
            await bot.send_message(ref_id, "✅ **Ваш реферал активировал бота!**\n\n"
                                           "Он успешно прошел все проверки подписки. "
                                           "💰 **Вам начислено +5 звезд на баланс!**")
        except: pass

@dp.callback_query(F.data == "profile")
async def profile_handler(call: types.CallbackQuery):
    reg, count = await database.get_user_stats(call.from_user.id)
    await call.message.edit_text(
        f"📊 **Твой личный кабинет**\n\n"
        f"📅 *Дата вступления:* `{reg}`\n"
        f"👥 *Всего приглашено:* `{count}` чел.\n"
        f"💎 *Твой текущий баланс:* `{count * 5}` **звезд**\n\n"
        f"--- \n*Приглашай больше — зарабатывай больше!*",
        reply_markup=get_main_kb()
    )

@dp.callback_query(F.data == "faq")
async def faq_handler(call: types.CallbackQuery):
    await call.message.edit_text(
        "📜 **Часто задаваемые вопросы:**\n\n"
        "1️⃣ **Как заработать?** — Приглашай друзей по своей ссылке.\n"
        "2️⃣ **Когда приходят звезды?** — Сразу после того, как приглашенный человек нажмет /start в этом боте.\n"
        "3️⃣ **За что дают звезды?** — За каждого активного пользователя, который прошел проверку подписки.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]])
    )

@dp.callback_query(F.data == "ref_link")
async def ref_link_handler(call: types.CallbackQuery):
    bot_info = await bot.get_me()
    await call.message.edit_text(
        f"🔗 **Твоя персональная ссылка:**\n\n"
        f"`https://t.me/{bot_info.username}?start={call.from_user.id}`\n\n"
        f"Скопируй её и отправь другу. После прохождения подписок он придет сюда, а ты получишь награду! 💸",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]])
    )

async def main():
    await database.init_db()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

