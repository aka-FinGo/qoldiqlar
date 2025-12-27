import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    # Render'dagi Environment Variable'dan o'qiydi
    # Agar topilmasa, xato bermasligi uchun None qaytaradi
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("❌ Xatolik: DATABASE_URL environment o'zgaruvchisi topilmadi!")
        return None

    try:
        # Neon DB va boshqa Postgres bazalar uchun ulanish
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"❌ Baza bilan ulanishda xato: {e}")
        return None
