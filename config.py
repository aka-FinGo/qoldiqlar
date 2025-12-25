import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@admin") # Agar topilmasa @admin bo'ladi

# --- KUCHAYTIRILGAN FAYL QIDIRUV ---
# Renderda fayl odatda shu yerda bo'ladi:
RENDER_PATH = "/etc/secrets/credentials.json"
# Lokal kompyuterda yoki GitHubda:
LOCAL_PATH = "credentials.json"

if os.path.exists(RENDER_PATH):
    CREDENTIALS_PATH = RENDER_PATH
    print(f"✅ Kalit topildi (Render): {CREDENTIALS_PATH}")
elif os.path.exists(LOCAL_PATH):
    CREDENTIALS_PATH = LOCAL_PATH
    print(f"✅ Kalit topildi (Lokal): {CREDENTIALS_PATH}")
else:
    CREDENTIALS_PATH = None
    print("❌ DIQQAT! credentials.json fayli topilmadi!")
