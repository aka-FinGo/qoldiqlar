import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# --- O'ZGARISH SHU YERDA ---
# Renderda Secret Files odatda "/etc/secrets/" papkasiga tushadi.
# Agar lokal kompyuterda bo'lsangiz, shunchaki "credentials.json" deb qidiradi.

if os.path.exists("/etc/secrets/credentials.json"):
    CREDENTIALS_PATH = "/etc/secrets/credentials.json"
else:
    CREDENTIALS_PATH = "credentials.json" # Telefonda yoki kompyuterda
