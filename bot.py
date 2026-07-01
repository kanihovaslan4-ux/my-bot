import asyncio, aiohttp
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flyerapi import Flyer
import database

TOKEN = "8659732625:AAFbCRywNhaX22_djBjYZYMFk57QpTFAURM"
PIARFLOW_API_KEY = "QcRQGGE2eIRWPIMQwd81O1OiM7RU9Pj4"
FLYER_API_KEY = "FL-WhOCyB-HiReli-Tmfdfy-uaoTSs"
PIARFLOW_API_URL = "https://piarflow.com/v1"
PAYMENT_CHANNEL_ID = -1001234567890 # УКАЖИ ID КАНАЛА ВЫПЛАТ

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
flyer = Flyer(FLYER_API_KEY)
pending_data = {}

async def piarflow_request(session, method, path, payload=None):
    headers = {"Authorization": f"Bearer {PIARFLOW_API_KEY}", "Content-Type": "application/json"}
    async with session.request(method, f"{PIARFLOW_API_URL}{path}", json=payload, headers=headers) as resp:
        return await resp.json(content_type=None)

def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🔗 Пригласить друзей", callback_data="ref_link")],
        [InlineKeyboardButton(text="💰 Вывод средств", callback_data="withdraw")],
        [InlineKeyboardButton(text="🎟 Канал выплат", url="https://t.me/gottec")]
    ])

@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject, session: aiohttp.ClientSession):
    await database.register_user_only(message.from_user.id, int(command.args) if command.args and command.args.isdigit() else None)
    pf_data = await piarflow_request(session, "POST", "/sponsors", {"user_id": message.from_user.id})
    pf_sponsors = pf_data.get("sponsors") or []
    
    if pf_sponsors:
        pending_data[message.from_user.id] = {"pf": [s["link"] for s in pf_sponsors], "fl": []}
        btns = [[InlineKeyboardButton(text="Подписаться", url=s["link"])] for s in pf_sponsors]
        btns.append([InlineKeyboardButton(text="✅ Проверить 1 этап", callback_data="check_pf")])
        await message.answer("🚀 **Этап 1 из 2**\nДля доступа к системе необходимо подписаться на спонсорские каналы. После подписки нажмите кнопку ниже.", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    else:
        await start_flyer(message, message.from_user.id)

async def start_flyer(message, user_id):
    tasks = await flyer.get_tasks(user_id) or []
    if not tasks:
        await message.answer("✅ Верификация успешно завершена!", reply_markup=get_main_kb())
        return
    pending_data[user_id] = {"pf": [], "fl": [t["signature"] for t in tasks]}
    btns = [[InlineKeyboardButton(text="Подписаться", url=t["url"])] for t in tasks]
    btns.append([InlineKeyboardButton(text="✅ Проверить 2 этап", callback_data="check_fl")])
    await message.answer("🔥 **Этап 2 из 2**\nОстался финальный шаг. Подпишитесь на каналы партнеров, чтобы активировать Личный Кабинет.", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data == "check_pf")
async def check_pf(call: types.CallbackQuery, session: aiohttp.ClientSession):
    res = await piarflow_request(session, "POST", "/sponsors/check", {"user_id": call.from_user.id, "links": pending_data[call.from_user.id]["pf"]})
    if all(s["status"] == "subscribed" for s in res.get("sponsors", [])):
        await start_flyer(call.message, call.from_user.id)
    else: await call.answer("❌ Вы подписались не на все каналы!", show_alert=True)

@router.callback_query(F.data == "check_fl")
async def check_fl(call: types.CallbackQuery):
    if all(await flyer.check_task(sig) == "subscribed" for sig in pending_data[call.from_user.id]["fl"]):
        await call.message.edit_text("✅ Доступ успешно открыт!", reply_markup=get_main_kb())
    else: await call.answer("❌ Вы подписались не на все каналы!", show_alert=True)

@router.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    reg, count, bal = await database.get_user_stats(call.from_user.id)
    await call.message.edit_text(f"💎 <b>ЛИЧНЫЙ КАБИНЕТ</b>\n\n👤 ID: <code>{call.from_user.id}</code>\n👥 Приглашено: {count}\n⭐️ Баланс: {bal} звезд\n\nПриглашайте друзей для увеличения дохода!", parse_mode="HTML", reply_markup=get_main_kb())

@router.callback_query(F.data == "ref_link")
async def ref_link(call: types.CallbackQuery):
    me = await bot.get_me()
    await call.message.edit_text(f"🔗 <b>ВАША РЕФЕРАЛЬНАЯ ССЫЛКА</b>\n\n<code>https://t.me/{me.username}?start={call.from_user.id}</code>\n\nРаспространяйте ссылку и получайте по 5 звезд за каждого нового пользователя!", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))

@router.callback_query(F.data == "withdraw")
async def withdraw(call: types.CallbackQuery):
    await call.message.edit_text("💰 Выберите сумму для вывода:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{s} звезд", callback_data=f"w_{s}")] for s in [15, 25, 50, 100]
    ]))

@router.callback_query(F.data.startswith("w_"))
async def process_w(call: types.CallbackQuery):
    amount = int(call.data.split("_")[1])
    _, _, bal = await database.get_user_stats(call.from_user.id)
    if bal < amount: return await call.answer("❌ Недостаточно средств!", show_alert=True)
    await database.withdraw_stars(call.from_user.id, amount)
    await bot.send_message(PAYMENT_CHANNEL_ID, f"🔔 <b>Новая заявка на вывод!</b>\n👤 User ID: {call.from_user.id}\n⭐️ Сумма: {amount} звезд", parse_mode="HTML")
    await call.message.edit_text(f"✅ Заявка на {amount} звезд успешно принята!", reply_markup=get_main_kb())

async def main():
    await database.init_db()
    async with aiohttp.ClientSession() as session:
        dp.workflow_data["session"] = session
        dp.include_router(router)
        await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
