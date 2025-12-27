import asyncio
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import Command # <--- SHU MUHIM
from aiogram.types import Message

from config import BOT_TOKEN
from bot.handlers import router as main_router 
import database.queries as db
from services.gsheets import get_all_users_from_sheet, get_all_remnants_from_sheet

# API funksiyalari
from services.api import (
    get_remnants, use_remnant, add_remnant, get_categories, 
    edit_remnant, delete_remnant, check_is_admin
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. SINXRONIZATSIYA VAZIFASI ---
async def full_sync_task():
    logger.info("🔄 GSheets -> DB Sinxronizatsiya boshlandi...")
    try:
        # A. Foydalanuvchi ruxsatlarini yangilash
        users = get_all_users_from_sheet() # Ruxsatlar!A2:D
        if users:
            for u in users:
                try:
                    # u[0] - UserID, u[3] - Status (A, B, C, D ustunlar)
                    # GSheets ustuniga qarab indeksni tekshiring: A=0, B=1, C=2, D=3
                    u_id = int(str(u[0]).strip())
                    u_status = 1 if str(u[3]).lower() in ['1', 'ha', 'true', 'bor', 'yes'] else 0
                    db.update_user_permission(u_id, u_status)
                    logger.info(f"👤 User {u_id} statusi {u_status} ga yangilandi.")
                except Exception as e:
                    logger.error(f"👤 User sync error: {e}")

        # B. Qoldiqlarni yangilash (A:Q)
        remnants = get_all_remnants_from_sheet() # Qoldiqlar!A2:Q
        if remnants:
            sync_count = 0
            for row in remnants:
                try:
                    db.sync_remnant_from_sheet(row)
                    sync_count += 1
                except: continue
            logger.info(f"✅ {sync_count} ta qoldiq yangilandi.")
            
    except Exception as e:
        logger.error(f"❌ TO'LIQ SYNC XATOSI: {e}")

# --- 2. BOT COMMANDS ---
@main_router.message(Command("sync"))
async def cmd_sync(message: Message):
    # Admin tekshiruvi (Ixtiyoriy)
    await message.answer("🔄 Sinxronizatsiya boshlandi... (Ruxsatlar + Qoldiqlar)")
    try:
        await full_sync_task()
        await message.answer("✅ Baza va Ruxsatlar muvaffaqiyatli yangilandi!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

# --- 3. WEB SERVER ---
async def start_web_server():
    app = web.Application()
    app.router.add_static('/static/', path='static')
    app.router.add_get('/webapp', lambda r: web.FileResponse('templates/index.html'))
    app.router.add_get('/api/remnants', get_remnants)
    app.router.add_get('/api/categories', get_categories)
    app.router.add_post('/api/use', use_remnant)
    app.router.add_post('/api/add', add_remnant)
    app.router.add_post('/api/edit', edit_remnant)
    app.router.add_post('/api/delete', delete_remnant)
    app.router.add_get('/api/check_admin', check_is_admin)
    app.router.add_get('/', lambda r: web.Response(text="Live"))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 10000)))
    await site.start()

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(main_router) # <--- ROUTER ULANGANINI TEKSHIRING
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
