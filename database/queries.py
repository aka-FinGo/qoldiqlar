from datetime import datetime
from database.connection import get_db_connection

# --- 1. QOLDIQ QIDIRISH (MUKAMMAL QIDIRUV) ---
def search_remnants(query_text):
    """Material yoki kategoriya bo'yicha qidirish (Pagination uchun jami ro'yxatni qaytaradi)"""
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor()
    try:
        # ILIKE - katta-kichik harfni farqlamay qidiradi
        query = """
            SELECT * FROM remnants 
            WHERE (material ILIKE %s OR category ILIKE %s) 
            AND status = 1
            ORDER BY id DESC
        """
        cursor.execute(query, (f"%{query_text}%", f"%{query_text}%"))
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Qidiruv xatosi: {e}")
        return []
    finally:
        conn.close()

# --- 2. DUBLIKATNI TEKSHIRISH ---
def check_duplicate(material, width, height, location):
    """Aynan bir xil o'lcham va materialdagi qoldiqni topish"""
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        query = """
            SELECT id, qty FROM remnants 
            WHERE material = %s AND width = %s AND height = %s AND location = %s 
            AND status = 1 
            LIMIT 1
        """
        cursor.execute(query, (material, width, height, location))
        return cursor.fetchone() # Topilsa dict qaytaradi, bo'lmasa None
    except Exception as e:
        print(f"❌ Dublikat tekshirish xatosi: {e}")
        return None
    finally:
        conn.close()

# --- 3. SONINI YANGILASH (DUBLIKAT TASDIQLANGANDA) ---
def update_qty(remnant_id, add_qty):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        # Avval eski sonini olamiz
        cursor.execute("SELECT qty FROM remnants WHERE id = %s", (remnant_id,))
        old_qty = cursor.fetchone()['qty']
        new_qty = old_qty + add_qty
        
        # Keyin yangilaymiz
        cursor.execute("UPDATE remnants SET qty = %s WHERE id = %s", (new_qty, remnant_id))
        conn.commit()
        return new_qty # Yangi sonni qaytaramiz
    except: return None
    finally: conn.close()

# --- 4. YANGI QOLDIQ QO'SHISH (FINAL) ---
def add_remnant_final(item, user_id, user_name):
    """Mutlaqo yangi qator qo'shish"""
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO remnants (
                category, material, width, height, qty, origin_order, location, created_by_user_id, created_by_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING id;
        """
        cursor.execute(query, (
            item.get('category', 'Boshqa'),
            item.get('material', 'Noma`lum'),
            item.get('width', 0),
            item.get('height', 0),
            item.get('qty', 1),
            item.get('order', ''),
            item.get('location', 'Sex'),
            user_id,
            user_name
        ))
        new_id = cursor.fetchone()['id']
        conn.commit()
        return new_id
    except Exception as e:
        print(f"❌ Qoldiq qo'shishda xato: {e}")
        return None
    finally:
        conn.close()

# --- 5. FOYDALANUVCHINI TEKSHIRISH VA YARATISH ---
def get_or_create_user(user_id, full_name, username):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (str(user_id),))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute(
                "INSERT INTO users (user_id, full_name, username, can_search, can_add) VALUES (%s, %s, %s, 0, 0)",
                (str(user_id), full_name, username)
            )
            conn.commit()
            return {"user_id": user_id, "can_search": 0, "can_add": 0, "is_new": True}
        return user
    finally:
        conn.close()

# --- 6. RUXSATLARNI YANGILASH (SYNC UCHUN) ---
def update_user_permission(user_id, status):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET can_search = %s, can_add = %s WHERE user_id = %s",
            (status, status, str(user_id))
        )
        conn.commit()
    finally:
        conn.close()

# --- 7. SHEETDAN TAHRIRLANGANDA YANGILASH ---
def sync_remnant_from_sheet(remnant_id, material, width, height, qty, location, status):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        # ID'dagi # belgisini olib tashlaymiz
        clean_id = int(str(remnant_id).replace('#', ''))
        query = """
            UPDATE remnants 
            SET material = %s, width = %s, height = %s, qty = %s, location = %s, status = %s
            WHERE id = %s
        """
        cursor.execute(query, (material, width, height, qty, location, status, clean_id))
        conn.commit()
    except Exception as e:
        print(f"❌ Sheetdan sync qilishda xato: {e}")
    finally:
        conn.close()


# --- 8. Qoldiqlarni qaytarib joyiga qo'yish (Undo) yoki kim ishlatganini bilish uchun bazaga status (1-bor, 0-ishlatilgan) va updated_at ---
def use_remnant(remnant_id, user_id):
    """Qoldiqni ishlatilgan (status=0) deb belgilash"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE remnants SET status = 0, used_by = %s, updated_at = %s WHERE id = %s",
            (user_id, datetime.now(), remnant_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally: conn.close()

def restore_remnant(remnant_id):
    """Xatolik bo'lsa, ishlatilgan qoldiqni qaytarish (status=1)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE remnants SET status = 1 WHERE id = %s", (remnant_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally: conn.close()

def get_remnant_details(remnant_id):
    """ID bo'yicha to'liq ma'lumotni olish"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM remnants WHERE id = %s", (remnant_id,))
        return cursor.fetchone()
    finally: conn.close()