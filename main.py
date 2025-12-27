import asyncio
import os
import logging
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
# Handlerlar routerini import qilamiz
from bot.handlers import router as main_router 
import database.queries as db
from services.gsheets import get_all_users_from_sheet, get_all_remnants_from_sheet

# --- API va WebApp funksiyalarini import qilamiz ---
from services.api import (
    get_remnants, use_remnant, add_remnant, get_categories, 
    edit_remnant, delete_remnant, check_is_admin
)

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. SINXRONIZATSIYA VAZIFASI ---
async def full_sync_task():
    logger.info("🔄 GSheets -> DB Sinxronizatsiya boshlandi...")
    try:
        # Userlarni yangilash
        users = get_all_users_from_sheet()
        if users:
            for row in users:
                try:
                    status = 1 if str(row[3]).lower() in ['1', 'true', 'ha', 'bor'] else 0
                    db.update_user_permission(row[0], status)
                except: continue
        
        # Qoldiqlarni yangilash
        remnants = get_all_remnants_from_sheet()
        if remnants:
            for r in remnants:
                try:
                    # Bazangizdagi ustunlarga mos indekslar (r[0]=id, r[1]=category, etc.)
                    db.sync_remnant_from_sheet(
                        r[0], r[1], r[2], int(r[3]), int(r[4]), 
                        int(r[5]), r[6], r[7], int(r[8])
                    )
                except: continue
        logger.info("✅ Sinxronizatsiya yakunlandi.")
    except Exception as e:
        logger.error(f"❌ Sync error: {e}")

# --- 2. BOTNI UYG'OQ TUTISH (SELF-PING) ---
async def self_ping():
    """Render uxlab qolmasligi uchun har 10 daqiqada o'ziga ping yuboradi"""
    # Render bergan URL manzilni bu yerga yozing
    app_url = "https://qoldiqlar.onrender.com/" 
    while True:
        await asyncio.sleep(600) # 10 daqiqa
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(app_url) as resp:
                    logger.info(f"🛰 Self-ping status: {resp.status}")
        except Exception as e:
            logger.error(f"🛰 Self-ping error: {e}")

# --- 3. WEB SERVER VA WEBAPP HANDLERLARI ---
async def web_app_handler(request):
    try:
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="Xatolik: templates/index.html topilmadi!", status=404)

async def handle_health_check(request):
    return web.Response(text="Bot & WebApp is Live")

async def start_web_server():
    app = web.Application()
    
    # Static fayllar (CSS, JS) uchun yo'l
    app.router.add_static('/static/', path='static', name='static')

    # Marshrutlar
    app.router.add_get('/webapp', web_app_handler)
    app.router.add_get('/api/remnants', get_remnants)
    app.router.add_get('/api/categories', get_categories)
    app.router.add_post('/api/use', use_remnant)
    app.router.add_post('/api/add', add_remnant)
    app.router.add_post('/api/edit', edit_remnant)
    app.router.add_post('/api/delete', delete_remnant)
    app.router.add_get('/api/check_admin', check_is_admin)
    app.router.add_get('/', handle_health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Web Server ishga tushdi: {port}-port")

# --- 4. ASOSIY ISHGA TUSHIRISH ---
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(main_router)
    
    # Web serverni ishga tushirish
    await start_web_server()

    # Self-ping vazifasini fonda ishga tushirish
    asyncio.create_task(self_ping())

    # Avtomatik sinxronizatsiya (Har 60 daqiqada)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(full_sync_task, "interval", minutes=60)
    scheduler.start()

    logger.info("🚀 Bot polling boshlandi...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Polling xatosi: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
