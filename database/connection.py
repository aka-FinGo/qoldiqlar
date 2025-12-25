import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_URL

def get_db_connection():
    """Neon.tech bazasiga ulanish hosil qiladi"""
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"❌ Bazaga ulanishda xatolik: {e}")
        return None
