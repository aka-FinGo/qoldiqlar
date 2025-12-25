import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from bot.handlers import router

# Loglarni yoqish (xatolarni ko'rish uchun)
logging.basicConfig(level=logging.INFO)

async def main():
    # 1. Botni yaratamiz
    bot = Bot(token=BOT_TOKEN)
    
    # 2. Dispatcher (Boshqaruvchi)
    dp = Dispatcher()
    
    # 3. Routerlarni ulaymiz (handlers.py dagi kodlarni)
    dp.include_router(router)
    
    print("🚀 Bot ishga tushdi! (Polling rejimi)")
    
    # 4. Botni o'chirmasdan eshitishni boshlaymiz
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot to'xtatildi.")
