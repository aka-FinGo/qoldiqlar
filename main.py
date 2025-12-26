import asyncio
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
# Handlerlar routerini import qilamiz
from bot.handlers import router as main_router 
import database.queries as db
from services.gsheets import get_all_users_from_sheet, get_all_remnants_from_sheet

# --- YANGI: API va WebApp funksiyalarini import qilamiz ---
# (Bu ishlashi uchun services/api.py fayli bo'lishi kerak)
from services.api import get_remnants, use_remnant, add_remnant, get_categories

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. SINXRONIZATSIYA VAZIFASI ---
async def full_sync_task():
    logger.info("🔄 Sinxronizatsiya boshlandi...")
    try:
        # Userlarni yangilash
        users = get_all_users_from_sheet()
        if users:
            for row in users:
                try:
                    status = 1 if str(row[2]).lower() in ['1', 'true', 'ha', 'bor'] else 0
                    db.update_user_permission(row[0], status)
                except: continue
        
        # Qoldiqlarni yangilash
        remnants = get_all_remnants_from_sheet()
        if remnants:
            for r in remnants:
                try:
                    # Indekslar: r[7]=Order, r[10]=Location, r[11]=Status
                    db.sync_remnant_from_sheet(
                        r[0], r[3], int(r[4]), int(r[5]), int(r[6]), 
                        r[7], r[10], int(r[11])
                    )
                except: continue
        logger.info("✅ Sinxronizatsiya yakunlandi.")
    except Exception as e:
        logger.error(f"❌ Sync error: {e}")

# --- 2. WEB SERVER VA WEBAPP HANDLERLARI ---

async def web_app_handler(request):
    """Mini Appning asosiy HTML faylini o'qib beradi"""
    try:
        with open('templates/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="Xatolik: templates/index.html fayli topilmadi! Iltimos uni yarating.", status=404)

async def handle_health_check(request):
    """Render bot o'chib qolmasligi uchun ping qiladigan manzil"""
    return web.Response(text="Bot & WebApp is Live")

async def start_web_server():
    app = web.Application()
    
    # --- MARSHRUTLAR (ROUTES) ---
    # 1. Web Appning asosiy ko'rinishi
    app.router.add_get('/webapp', web_app_handler)
    
    # 2. Frontend uchun APIlar (Ma'lumot olish/yuborish)
    app.router.add_get('/api/remnants', get_remnants)
    app.router.add_get('/api/categories', get_categories)
    app.router.add_post('/api/use', use_remnant)
    app.router.add_post('/api/add', add_remnant)
    app.router.add_post('/api/edit', edit_remnant)
app.router.add_post('/api/delete', delete_remnant)
app.router.add_get('/api/check_admin', check_is_admin)

    # 3. Oddiy Health Check (Bot ishlayaptimi yo'qmi bilish uchun)
    app.router.add_get('/', handle_health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    await site.start()
    logger.info(f"✅ Web Server (Bot + Mini App) {port}-portda ishga tushdi.")

# --- 3. ASOSIY ISHGA TUSHIRISH ---
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(main_router)
    
    # Web serverni (API va App bilan birga) ishga tushiramiz
    await start_web_server()

    # Avtomatik sinxronizatsiya (Har 60 daqiqada - optimal vaqt)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(full_sync_task, "interval", minutes=60)
    scheduler.start()

    logger.info("🚀 Bot polling boshlandi...")
    try:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except: pass

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
