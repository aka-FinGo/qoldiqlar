import asyncio
import os
import aiohttp
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from bot.handlers import router
import database.queries as db
from services.gsheets import get_all_users_from_sheet, get_all_remnants_from_sheet

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
                    db.sync_remnant_from_sheet(r[0], r[3], int(r[4]), int(r[5]), int(r[6]), r[10], int(r[11]))
                except: continue
        logger.info("✅ Sinxronizatsiya yakunlandi.")
    except Exception as e:
        logger.error(f"❌ Sync error: {e}")

# --- 2. WEB SERVER FUNKSIYALARI ---
async def handle(request):
    return web.Response(text="Bot is Live")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render portni muhit o'zgaruvchisidan oladi
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    # MANA SHU QATOR ENDI FUNKSIYA ICHIDA (XATO BO'LMAYDI)
    await site.start()
    logger.info(f"✅ Web server {port}-portda ishga tushdi.")

# --- 3. ASOSIY ISHGA TUSHIRISH ---
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Web serverni ishga tushiramiz
    await start_web_server()

    # Sinxronizatsiyani ishga tushiramiz (Har 10 daqiqada)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(full_sync_task, "interval", minutes=10)
    scheduler.start()

    logger.info("🚀 Bot polling boshlandi...")
    try:
        # Tarmoq xatosi bo'lsa ham bot o'chib qolmasligi uchun
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            logger.warning(f"Webhook o'chirishda xato (e'tiborsiz qoldiring): {e}")

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
