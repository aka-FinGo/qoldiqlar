import asyncio, os, aiohttp, logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN
from bot.handlers import router
import database.queries as db
from services.gsheets import get_all_users_from_sheet, get_all_remnants_from_sheet

# --- SINXRONIZATSIYA VAZIFASI ---
async def full_sync_task():
    print("🔄 Sinxronizatsiya boshlandi...")
    # 1. Ruxsatlarni yangilash
    users = get_all_users_from_sheet()
    for row in users:
        try:
            status = 1 if str(row[2]).lower() in ['1', 'true', 'ha'] else 0
            db.update_user_permission(row[0], status)
        except: continue
    
    # 2. Qoldiqlarni yangilash (Excelda o'zgartirilgan bo'lsa)
    remnants = get_all_remnants_from_sheet()
    for r in remnants:
        try:
            db.sync_remnant_from_sheet(r[0], r[3], int(r[4]), int(r[5]), int(r[6]), r[10], int(r[11]))
        except: continue
    
    # 3. Render Self-Ping
    url = os.getenv("RENDER_EXTERNAL_URL")
    if url:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp: print(f"Ping: {resp.status}")
    print("✅ Sinxronizatsiya yakunlandi.")

# --- WEB SERVER (Health Check) ---
async def handle(request): return web.Response(text="Bot is Live")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Web server
    app = web.Application(); app.router.add_get('/', handle)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 10000))).start()

    # Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(full_sync_task, "interval", minutes=10)
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
