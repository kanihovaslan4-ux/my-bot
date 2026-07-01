import asyncio
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiohttp import web
from flyerapi import Flyer
import database

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8659732625:AAFbCRywNhaX22_djBjYZYMFk57QpTFAURM"
PIARFLOW_API_KEY = "QcRQGGE2eIRWPIMQwd81O1OiM7RU9Pj4"
FLYER_API_KEY = "FL-WhOCyB-HiReli-Tmfdfy-uaoTSs"
PIARFLOW_API_URL = "https://piarflow.com/v1"
ADMIN_ID = 7880039240
CHANNEL_LINK = "https://t.me/gottec"
PAYMENT_CHANNEL_ID = -1003903368955  # УКАЖИ ЗДЕСЬ ID КАНАЛА ВЫПЛАТ
TELEGRAPH_URL = "https://telegra.ph/PravilaFAQ-06-30"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
flyer = Flyer(FLYER_API_KEY)
pending_data = {}

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def piarflow_request(session, method, path, payload=None):
    headers = {"Authorization": f"Bearer {PIARFLOW_API_KEY}", "Content-Type": "application/json"}
    async with session.request(method, f"{PIARFLOW_API_URL}{path}", json=payload, headers=headers) as resp:
        return await resp.json(content_type=None)

def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🔗 Пригласить друзей", callback_data="ref_link")],
        [InlineKeyboardButton(text="💰 Вывод средств", callback_data="withdraw")],
        [InlineKeyboardButton(text="🎟 Канал выплат", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="📜 Правила и FAQ", web_app=WebAppInfo(url=TELEGRAPH_URL))]
    ])

# --- ЛОГИКА ЭТАПОВ ПОДПИСКИ ---
@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject, session: aiohttp.ClientSession):
    user_id = message.from_user.id
    ref_id = int(command.args) if command.args and command.args.isdigit() else None
    await database.register_user_only(user_id, ref_id)
    
    pf_data = await piarflow_request(session, "POST", "/sponsors", {"user_id": user_id, "chat_id": message.chat.id})
    pf_sponsors = pf_data.get("sponsors") or []
    
    if pf_sponsors:
        pending_data[user_id] = {"pf_links": [s["link"] for s in pf_sponsors], "fl_sigs": []}
        buttons = [[InlineKeyboardButton(text="Подписаться на спонсора", url=s["link"])] for s in pf_sponsors]
        buttons.append([InlineKeyboardButton(text="✅ Проверить 1 этап", callback_data="check_pf")])
        await message.answer("🚀 **Добро пожаловать!**\nЧтобы начать пользоваться ботом, пройдите обязательную верификацию. Это стандартная процедура для доступа к нашей системе заработка.\n\nНажмите кнопку ниже после подписки.", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await start_flyer_stage(message, user_id)

async def start_flyer_stage(message: types.Message, user_id: int):
    fl_tasks = await flyer.get_tasks(user_id) or []
    if not fl_tasks:
        return await message.answer("👋 Привет! Добро пожаловать в систему. Вы уже прошли проверку.", reply_markup=get_main_kb())
    
    if user_id not in pending_data: pending_data[user_id] = {"pf_links": [], "fl_sigs": []}
    pending_data[user_id]["fl_sigs"] = [t["signature"] for t in fl_tasks]
    
    buttons = [[InlineKeyboardButton(text="Подписаться", url=t["url"])] for t in fl_tasks]
    buttons.append([InlineKeyboardButton(text="✅ Проверить 2 этап", callback_data="check_fl")])
    await message.answer("🔥 **Второй этап верификации**\nПочти готово! Подпишитесь на каналы наших партнеров, чтобы активировать доступ к личному кабинету и выводу средств.", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "check_pf")
async def check_pf_handler(call: types.CallbackQuery, session: aiohttp.ClientSession):
    pf_res = await piarflow_request(session, "POST", "/sponsors/check", {"user_id": call.from_user.id, "links": pending_data[call.from_user.id]["pf_links"]})
    if all(s.get("status") == "subscribed" for s in pf_res.get("sponsors", [])):
        await call.message.edit_text("✅ Этап 1 пройден. Переходим далее...")
        await start_flyer_stage(call.message, call.from_user.id)
    else:
        await call.answer("❌ Подпишитесь на все каналы первого этапа!", show_alert=True)

@router.callback_query(F.data == "check_fl")
async def check_fl_handler(call: types.CallbackQuery):
    fl_ok = all(await flyer.check_task(sig) == "subscribed" for sig in pending_data[call.from_user.id]["fl_sigs"])
    if fl_ok:
        await call.message.edit_text("✅ Все этапы пройдены! Доступ открыт.", reply_markup=get_main_kb())
        pending_data.pop(call.from_user.id, None)
    else:
        await call.answer("❌ Не все каналы второго этапа подтверждены.", show_alert=True)

# --- ОСНОВНОЙ ФУНКЦИОНАЛ ---
@router.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    reg, count = await database.get_user_stats(call.from_user.id)
    text = (f"💎 <b>Личный кабинет</b> 💎\n\n"
            f"👤 <b>Ваш уникальный ID:</b> <code>{call.from_user.id}</code>\n"
            f"📅 <b>Дата регистрации:</b> {reg}\n"
            f"👥 <b>Количество приглашенных друзей:</b> {count}\n\n"
            f"⭐️ <b>Текущий баланс:</b> {count * 5} звезд\n\n"
            f"<i>Статус аккаунта:</i> ✅ Верифицирован\n"
            f"<i>Наш проект предлагает лучшие условия для заработка. Приглашайте новых пользователей и увеличивайте свой капитал!</i>")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_kb())

@router.callback_query(F.data == "ref_link")
async def ref_link_handler(call: types.CallbackQuery):
    me = await bot.get_me()
    text = (f"<b>🔗 ВАША ПЕРСОНАЛЬНАЯ РЕФЕРАЛЬНАЯ ССЫЛКА</b>\n\n"
            f"<code>https://t.me/{me.username}?start={call.from_user.id}</code>\n\n"
            f"💎 <b>Условия программы:</b>\n"
            f"За каждого приглашенного пользователя, который пройдет верификацию, вы получаете <b>5 звезд</b> на баланс. "
            f"Копируйте ссылку и распространяйте её в тематических сообществах для максимизации прибыли!")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))

@router.callback_query(F.data == "withdraw")
async def withdraw(call: types.CallbackQuery):
    await bot.send_message(PAYMENT_CHANNEL_ID, f"🔔 <b>Новая заявка на вывод!</b>\n👤 <b>User ID:</b> {call.from_user.id}\n⭐️ <b>Сумма:</b> { (await database.get_user_stats(call.from_user.id))[1] * 5 } звезд")
    await call.answer("✅ Заявка на вывод успешно отправлена администраторам. Ожидайте уведомления в канале выплат.", show_alert=True)

# --- ЗАПУСК ---
async def main():
    await database.init_db()
    # Веб-сервер здесь... (как был)
    async with aiohttp.ClientSession() as session:
        dp.workflow_data["session"] = session
        dp.include_router(router)
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



