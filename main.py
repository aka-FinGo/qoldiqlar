import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from bot.handlers import router

# --- YANGI QO'SHILGAN QISM (WEB SERVER) ---
from aiohttp import web

async def health_check(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render kutayotgan portni ochamiz (odatda 10000)
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌍 Soxta Web Server {port}-portda ishga tushdi")
# -------------------------------------------

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Web serverni fonda ishga tushiramiz
    await start_web_server()
    
    print("🚀 Bot ishga tushdi! (Polling rejimi)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot to'xtatildi.")
