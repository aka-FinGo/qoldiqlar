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

# Loglarni sozlash (Xatolarni ko'rish uchun)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Render portni muhit o'zgaruvchisidan oladi, topolmasa 10000 ishlatadi
port = int(os.getenv("PORT", 10000))
site = web.TCPSite(runner, '0.0.0.0', port)
await site.start()
# --- SINXRONIZATSIYA VAZIFASI ---
async def full_sync_task():
    logger.info("🔄 Sinxronizatsiya boshlandi...")
    try:
        # 1. Ruxsatlarni yangilash
        users = get_all_users_from_sheet()
        if users:
            for row in users:
                try:
                    if len(row) >= 3:
                        status = 1 if str(row[2]).lower() in ['1', 'true', 'ha', 'bor'] else 0
                        db.update_user_permission(row[0], status)
                except Exception as e:
                    logger.error(f"User sync error: {e}")
        
        # 2. Qoldiqlarni yangilash (Excelda o'zgartirilgan bo'lsa)
        remnants = get_all_remnants_from_sheet()
        if remnants:
            for r in remnants:
                try:
                    # r[0] - ID, r[3] - material, r[4] - width, r[5] - height, r[6] - qty, r[10] - location, r[11] - status
                    db.sync_remnant_from_sheet(r[0], r[3], int(r[4]), int(r[5]), int(r[6]), r[10], int(r[11]))
                except Exception as e:
                    logger.error(f"Remnant sync error: {e}")

        # 3. Render Self-Ping (Botni uyg'oq saqlash uchun)
        url = os.getenv("RENDER_EXTERNAL_URL")
        if url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    logger.info(f"Self-Ping yuborildi: {resp.status}")

        logger.info("✅ Sinxronizatsiya yakunlandi.")
    except Exception as e:
        logger.error(f"❌ Sinxronizatsiyada umumiy xato: {e}")

# --- WEB SERVER (Health Check) ---
async def handle(request):
    return web.Response(text="Bot is Live and Active!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render portni muhit o'zgaruvchisidan oladi
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Web server {port}-portda ishga tushdi.")

# --- ASOSIY MAIN FUNKSIYA ---
async def main():
    # Bot va Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    # 1. Web serverni ishga tushirish (Render port xatosini yo'qotadi)
    await start_web_server()

    # 2. Scheduler (Har 10 daqiqada sinxronizatsiya)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(full_sync_task, "interval", minutes=10)
    scheduler.start()
    logger.info("⏰ Scheduler ishga tushdi.")

    # 3. Botni ishga tushirish (Polling)
    logger.info("🚀 Bot polling boshlandi...")
    try:
        # Eskirgan xabarlarni o'chirib tashlash (Conflict bo'lmasligi uchun)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi!")
