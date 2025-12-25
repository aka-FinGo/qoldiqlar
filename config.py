import os
from dotenv import load_dotenv

# .env faylni o'qiymiz (agar lokal kompyuterda bo'lsa)
load_dotenv()

# Telegram Bot Tokeni
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Neon.tech bazasi manzili (postgres://...)
DB_URL = os.getenv("DATABASE_URL")

# Groq AI kaliti
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Adminlarning ID raqamlari (vergul bilan ajratilgan bo'lsa, listga o'giramiz)
ADMINS = [int(x) for x in os.getenv("ADMIN_ID", "").split(",") if x]
