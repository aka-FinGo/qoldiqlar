import asyncio
import os
import logging
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from bot.handlers import router as main_router 
import database.queries as db # <--- MUHIM: db importi joyida bo'lishi kerak
from services.gsheets import get_all_users_from_sheet, get_all_remnants_from_sheet

# API funksiyalari
from services.api import (
    get_remnants, use_remnant, add_remnant, get_categories, 
    edit_remnant, delete_remnant, check_is_admin
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. SINXRONIZATSIYA VAZIFASI (A-Q) ---
async def full_sync_task():
    logger.info("🔄 GSheets -> DB Sinxronizatsiya boshlandi (A-Q)...")
    try:
        # Userlarni yangilash
        users = get_all_users_from_sheet()
        if users:
            for u in users:
                try: 
                    # users sheetida odatda r[0]=id, r[3]=status
                    db.update_user_permission(u[0], 1 if str(u[3]).lower() in ['1','ha','true','bor'] else 0)
                except: continue
        
        # Qoldiqlarni yangilash (A:Q - 17 ta ustun)
        remnants = get_all_remnants_from_sheet() 
        if remnants:
            sync_count = 0
            for row in remnants:
                try:
                    # queries.py ichidagi yangi 17 talik funksiyani chaqiramiz
                    db.sync_remnant_from_sheet(row)
                    sync_count += 1
                except Exception as e:
                    logger.error(f"Row sync error: {e}")
            logger.info(f"✅ {sync_count} ta qator muvaffaqiyatli yangilandi.")
        
    except Exception as e:
        logger.error(f"❌ Sync Error: {e}")

# --- 2. COMMAND HANDLERLAR ---
# Bu handler main_router ga ulanishi kerak
@main_router.message(Command("sync"))
async def cmd_sync(message: Message):
    # Admin tekshiruvi (Ixtiyoriy lekin tavsiya etiladi)
    await message.answer("🔄 Baza Google Sheets (A-Q) bilan tenglashtirilmoqda, kuting...")
    try:
        await full_sync_task()
        await message.answer("✅ Sinxronizatsiya yakunlandi! Barcha 17 ta ustun (A-Q) yangilandi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}")

# --- 3. WEB SERVER ---
async def web_app_handler(request):
    try:
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    except:
        return web.Response(text="index.html topilmadi", status=404)

async def start_web_server():
    app = web.Application()
    app.router.add_static('/static/', path='static', name='static')
    
    app.router.add_get('/webapp', web_app_handler)
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
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Web Server {port}-portda ishga tushdi.")

# --- 4. ASOSIY START ---
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # MUHIM: Routerni ulash
    dp.include_router(main_router)
    
    await start_web_server()

    # Avtomatik sinxronizatsiya (Har 60 daqiqada)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(full_sync_task, "interval", minutes=60)
    scheduler.start()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
