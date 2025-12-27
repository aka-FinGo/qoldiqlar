import asyncio
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from services.api import (
    get_remnants, use_remnant, add_remnant, get_categories, 
    edit_remnant, delete_remnant, check_is_admin
)
from bot.handlers import router as main_router
from config import BOT_TOKEN

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
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 10000)))
    await site.start()

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(main_router)
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
