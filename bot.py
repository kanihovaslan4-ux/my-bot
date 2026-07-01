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
TELEGRAPH_URL = "https://telegra.ph/PravilaFAQ-06-30"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
flyer = Flyer(FLYER_API_KEY)
# Хранилище временных данных: user_id -> {'pf_links': [], 'fl_sigs': []}
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

# --- ЛОГИКА СТАРТА И ПРОВЕРКИ ---
@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject, session: aiohttp.ClientSession):
    user_id = message.from_user.id
    # Регистрация в БД
    ref_id = int(command.args) if command.args and command.args.isdigit() else None
    await database.register_user_only(user_id, ref_id)
    
    # 1. Получаем спонсоров Piarflow
    pf_data = await piarflow_request(session, "POST", "/sponsors", {"user_id": user_id, "chat_id": message.chat.id})
    pf_sponsors = pf_data.get("sponsors") or []
    
    # 2. Получаем задачи FlyerAPI
    fl_tasks = await flyer.get_tasks(user_id) or []
    
    # Если задач нет ни там, ни там - пускаем сразу
    if not pf_sponsors and not fl_tasks:
        return await message.answer("👋 Привет! Доступ открыт.", reply_markup=get_main_kb())

    # Сохраняем данные для проверки
    pending_data[user_id] = {
        "pf_links": [s["link"] for s in pf_sponsors],
        "fl_sigs": [t["signature"] for t in fl_tasks]
    }

    # Создаем кнопки (сначала Piarflow, потом Flyer)
    buttons = []
    for s in pf_sponsors: buttons.append([InlineKeyboardButton(text="Подписаться (Сервис 1)", url=s["link"])])
    for t in fl_tasks: buttons.append([InlineKeyboardButton(text="Подписаться (Сервис 2)", url=t["url"])])
    buttons.append([InlineKeyboardButton(text="✅ Проверить все подписки", callback_data="check_all")])
    
    await message.answer("🚀 Для доступа к боту выполните задания спонсоров:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "check_all")
async def check_all_handler(call: types.CallbackQuery, session: aiohttp.ClientSession):
    user_id = call.from_user.id
    data = pending_data.get(user_id)
    
    if not data:
        return await call.message.edit_text("Меню:", reply_markup=get_main_kb())

    # 1. Проверка Piarflow
    pf_res = await piarflow_request(session, "POST", "/sponsors/check", {"user_id": user_id, "links": data["pf_links"]})
    pf_ok = all(s.get("status") == "subscribed" for s in pf_res.get("sponsors", []))
    
    # 2. Проверка FlyerAPI
    fl_ok = True
    for sig in data["fl_sigs"]:
        status = await flyer.check_task(sig)
        if status != "subscribed":
            fl_ok = False
            break
            
    if pf_ok and fl_ok:
        await call.message.edit_text("✅ Поздравляем! Все подписки подтверждены.", reply_markup=get_main_kb())
        pending_data.pop(user_id, None)
    else:
        await call.answer("❌ Подписки не найдены! Проверьте все каналы.", show_alert=True)

# --- ПРОФИЛЬ И РЕФЕРАЛЫ ---
@router.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    reg, count = await database.get_user_stats(call.from_user.id)
    text = (f"💎 <b>ЛИЧНЫЙ КАБИНЕТ</b> 💎\n\n"
            f"👤 <b>ID:</b> <code>{call.from_user.id}</code>\n"
            f"👥 <b>Приглашено:</b> {count}\n"
            f"⭐️ <b>Баланс:</b> {count * 5} звезд")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_kb())

@router.callback_query(F.data == "ref_link")
async def ref_link_handler(call: types.CallbackQuery):
    me = await bot.get_me()
    text = f"<b>🔗 Твоя ссылка:</b>\n<code>https://t.me/{me.username}?start={call.from_user.id}</code>"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))

# --- АДМИНКА ---
@router.message(Command("admin"))
async def admin(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("🛠 Админ-панель: /send [текст], /promo [код] [сумма] [лимит]")

@router.message(F.text.startswith("/send"))
async def send_all(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    text = msg.text.replace("/send ", "")
    for uid in await database.get_all_users():
        try: await bot.send_message(uid, text)
        except: continue
    await msg.answer("✅ Готово")

# --- СЕРВЕР И ЗАПУСК ---
async def start_web():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Running"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000))).start()

async def main():
    await database.init_db()
    await start_web()
    async with aiohttp.ClientSession() as session:
        dp.workflow_data["session"] = session
        dp.include_router(router)
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

### Что нужно сделать прямо сейчас:
1.  **requirements.txt**: Добавь туда `flyerapi`.
2.  **Деплой**: Замени код и нажми Deploy на Render.

Теперь у тебя "двойной фильтр" подписок. Если юзер подписывается на всё, ты получаешь деньги с двух площадок сразу! Удачи с первыми серьезными выплатами!



