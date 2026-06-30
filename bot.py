from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiohttp import web
import database, asyncio, os

TOKEN = "8659732625:AAHZ3VLuGhzPuFSiNRcqMVLec4BDJ0qDjeo"
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
    await message.answer("<b>👋 Привет! Добро пожаловать!</b>\n\nИспользуй меню ниже для работы:", parse_mode="HTML", reply_markup=get_main_kb())
    ref_id = await database.pay_reward(message.from_user.id)
    if ref_id:
        try: await bot.send_message(ref_id, "✅ <b>Друг активировал бота!</b>\n💰 <i>+5 звезд начислено!</i>", parse_mode="HTML")
        except: pass

@dp.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    reg, count = await database.get_user_stats(call.from_user.id)
    await call.message.edit_text(f"<b>📊 ЛИЧНЫЙ КАБИНЕТ</b>\n━━━━━━━━━━━━━━━━━━━\n🗓 В системе с: <code>{reg}</code>\n👥 Приглашено: <b>{count}</b>\n💎 Баланс: <b>{count * 5}</b> ⭐️", parse_mode="HTML", reply_markup=get_main_kb())

@dp.callback_query(F.data == "ref_link")
async def ref_link_handler(call: types.CallbackQuery):
    bot_info = await bot.get_me()
    await call.message.answer(f"<b>🔗 Твоя ссылка:</b>\n<code>https://t.me/{bot_info.username}?start={call.from_user.id}</code>\n\n💎
<b>🌟 Как работает наша реферальная программа?</b>

Хотите увеличить свой баланс и получать бонусы? Мы сделали это максимально просто и прозрачно! Следуйте нашей инструкции, чтобы начать зарабатывать <b>Звезды (⭐️)</b> прямо сейчас.

🚀 <b>Пошаговая инструкция:</b>

• <b>Шаг 1: Получите личную ссылку</b> 🔗
Откройте раздел реферальной программы и скопируйте свою <b>уникальную ссылку</b>. Это ваш персональный инструмент для привлечения новых участников.

• <b>Шаг 2: Приглашайте друзей</b> 📣
Отправляйте ссылку знакомым или публикуйте её в своих сообществах. Чем шире круг охвата, тем больше ваш бонус.

• <b>Шаг 3: Выполнение условий</b> ✅
Система фиксирует переход по ссылке, но <b>награда начисляется только после подписки</b> на все обязательные каналы. Это строгое правило!

• <b>Шаг 4: Получите свои Звезды</b> 🎁
Как только ваш друг подпишется на все каналы, <b>5 Звезд (⭐️)</b> автоматически поступят на ваш счет. Никаких ожиданий — всё происходит моментально!

⚠️ <b>Важная информация:</b>

• <b>Гарантия честности:</b> Награда поступает <b>только</b> после проверки подписки. Если подписка не оформлена — система не начислит бонус.
• <b>Без ограничений:</b> Приглашайте столько людей, сколько пожелаете. Каждое качественное приглашение приносит вам <b>5 Звезд (⭐️)</b>.

<b>Готовы начать?</b> Скопируйте ссылку и приступайте к сбору бонусов прямо сейчас! 🚀
"""

# В функции отправки сообщения укажите parse_mode='HTML'
await message.answer(text, parse_mode='HTML')
</i>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))

@dp.callback_query(F.data == "withdraw")
async def withdraw_menu(call: types.CallbackQuery):
    _, count = await database.get_user_stats(call.from_user.id)
    if count * 5 < 15: return await call.answer("⚠️ Минимум 15 звезд!", show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{s} ⭐️", callback_data=f"w_{s}")] for s in [15, 25, 50, 100]] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]])
    await call.message.edit_text("<b>💰 ВЫБЕРИ СУММУ</b>", parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data.startswith("w_"))
async def request_withdraw(call: types.CallbackQuery):
    amount = int(call.data.split("_")[1])
    await database.create_withdrawal(call.from_user.id, amount)
    await call.message.edit_text("✅ <b>Заявка оформлена!</b>\nСледи за каналом выплат.", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎟 Перейти в канал", url=CHANNEL_LINK)], [InlineKeyboardButton(text="🏠 Назад", callback_data="profile")]]))

async def main():
    await database.init_db()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
