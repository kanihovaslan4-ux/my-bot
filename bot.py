from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiohttp import web
import database, asyncio, os, aiohttp

TOKEN = "8659732625:AAFbCRywNhaX22_djBjYZYMFk57QpTFAURM"
PIARFLOW_API_KEY = "QcRQGGE2eIRWPIMQwd81O1OiM7RU9Pj4"
PIARFLOW_API_URL = "https://piarflow.com/v1"
CHANNEL_LINK = "https://t.me/gottec"
TELEGRAPH_URL = "https://telegra.ph/PravilaFAQ-06-30"
ADMIN_ID = 7880039240 

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
pending_links = {}

# --- ИНТЕГРАЦИЯ PIARFLOW ---
async def piarflow_request(session, method, path, payload=None):
    async with session.request(method, f"{PIARFLOW_API_URL}{path}", json=payload, 
                               headers={"Authorization": f"Bearer {PIARFLOW_API_KEY}", "Content-Type": "application/json"}) as response:
        return await response.json(content_type=None)

# --- ВЕБ-СЕРВЕР ---
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

# --- ЛОГИКА ПОДПИСОК ---
@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject, session: aiohttp.ClientSession):
    user_id = message.from_user.id
    # Регистрация
    await database.register_user_only(user_id, int(command.args) if command.args and command.args.isdigit() else None)
    
    # Запрос спонсоров
    tasks = await piarflow_request(session, "POST", "/sponsors", {"user_id": user_id, "chat_id": message.chat.id})
    sponsors = tasks.get("sponsors") or []
    
    if not sponsors:
        return await message.answer("👋 Привет! Добро пожаловать в систему.", reply_markup=get_main_kb())

    pending_links[user_id] = [s["link"] for s in sponsors]
    buttons = [[InlineKeyboardButton(text="Подписаться", url=s["link"])] for s in sponsors]
    buttons.append([InlineKeyboardButton(text="✅ Проверить подписку", callback_data="piarflow:check")])
    await message.answer("Для доступа к функциям бота подпишитесь на каналы:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "piarflow:check")
async def check_handler(callback: types.CallbackQuery, session: aiohttp.ClientSession):
    user_id = callback.from_user.id
    links = pending_links.get(user_id, [])
    result = await piarflow_request(session, "POST", "/sponsors/check", {"user_id": user_id, "links": links})
    
    if all(item.get("status") == "subscribed" for item in result.get("sponsors", [])):
        await callback.message.edit_text("✅ Доступ открыт! Используйте кнопки:", reply_markup=get_main_kb())
        pending_links.pop(user_id, None)
    else:
        await callback.answer("❌ Вы подписались не на все каналы!", show_alert=True)

# --- ТВОИ ХЕНДЛЕРЫ ---
@router.callback_query(F.data == "profile")
async def profile(call: types.CallbackQuery):
    reg, count = await database.get_user_stats(call.from_user.id)
    text = f"💎 <b>ЛИЧНЫЙ КАБИНЕТ</b> 💎\n\n👤 <b>ID:</b> <code>{call.from_user.id}</code>\n📅 <b>В системе с:</b> {reg}\n👥 <b>Приглашено:</b> {count}\n\n⭐️ <b>Твой баланс:</b> {count * 5} звезд"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_kb())

@router.callback_query(F.data == "ref_link")
async def ref_link_handler(call: types.CallbackQuery):
    bot_info = await bot.get_me()
    text = f"<b>🔗 Твоя ссылка:</b>\n<code>https://t.me/{bot_info.username}?start={call.from_user.id}</code>\n\n💎 <b>Приглашай друзей и получай 5 звезд за каждого!</b>"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")]]))

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🛠 <b>Админ-панель:</b>\n\n/promo [код] [сумма] [использования]\n/send [текст] - рассылка")

@router.message(F.text.startswith("/send"))
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/send ", "")
    for user_id in await database.get_all_users():
        try: await bot.send_message(user_id, text)
        except: continue
    await message.answer("✅ Рассылка завершена.")

# --- ЗАПУСК ---
async def main():
    await database.init_db()
    await start_web_server()
    async with aiohttp.ClientSession() as session:
        dp.workflow_data["session"] = session
        dp.include_router(router)
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


