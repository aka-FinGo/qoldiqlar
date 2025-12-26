from datetime import datetime
from database.connection import get_db_connection

# --- 1. QOLDIQ QIDIRISH (MUKAMMAL QIDIRUV) ---
def search_remnants(query_text):
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor()
    try:
        # User "ishlatilgan" deb yozganini tekshirish
        is_used_search = "ishlatilgan" in query_text.lower()
        status_filter = 0 if is_used_search else 1
        
        # Qidiruv so'zini tozalash
        clean_query = query_text.lower().replace("ishlatilgan", "").strip()
        
        # Agar so'z juda qisqa bo'lsa (masalan shunchaki "ishlatilgan"), hamma status 0 larni chiqaradi
        search_param = f"%{clean_query}%"
        
        query = """
            SELECT * FROM remnants 
            WHERE (material ILIKE %s OR category ILIKE %s OR CAST(id AS TEXT) ILIKE %s) 
            AND status = %s
            ORDER BY id DESC
        """
        cursor.execute(query, (search_param, search_param, search_param, status_filter))
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Qidiruv xatosi (SQL): {e}") # Render logda buni ko'rasiz
        return []
    finally:
        conn.close()


def get_used_remnants(user_id=None):
    """Ishlatilgan qoldiqlarni olish (Agar user_id berilsa, faqat o'zinikini)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if user_id:
            query = "SELECT * FROM remnants WHERE status = 0 AND used_by = %s ORDER BY updated_at DESC"
            cursor.execute(query, (str(user_id),))
        else:
            query = "SELECT * FROM remnants WHERE status = 0 ORDER BY updated_at DESC"
            cursor.execute(query)
        return cursor.fetchall()
    finally: conn.close()

def get_all_active_remnants():
    """Barcha mavjud (status=1) qoldiqlarni ro'yxat shaklida olish"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM remnants WHERE status = 1 ORDER BY id DESC")
        return cursor.fetchall()
    finally: conn.close()
        

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
def sync_remnant_from_sheet(r_id, material, width, height, qty, order_no, location, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # ID mavjud bo'lsa yangilaydi, bo'lmasa qo'shadi (UPSERT)
        query = """
            INSERT INTO remnants (id, material, width, height, qty, origin_order, location, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
            material=EXCLUDED.material, width=EXCLUDED.width, height=EXCLUDED.height, 
            qty=EXCLUDED.qty, origin_order=EXCLUDED.origin_order, 
            location=EXCLUDED.location, status=EXCLUDED.status;
        """
        cursor.execute(query, (r_id.replace('#',''), material, width, height, qty, order_no, location, status))
        conn.commit()
    except Exception as e:
        print(f"❌ Sheetdan sync qilishda xato: {e}")
    finally:
        conn.close()


# --- 8. Qoldiqlarni qaytarib joyiga qo'yish (Undo) yoki kim ishlatganini bilish uchun bazaga status (1-bor, 0-ishlatilgan) va updated_at ---
def use_remnant(remnant_id, user_id):
    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        # Statusni 0 qilamiz, ishlatgan odam IDsi va vaqtini yozamiz
        cursor.execute(
            "UPDATE remnants SET status = 0, used_by = %s, updated_at = NOW() WHERE id = %s AND status = 1",
            (str(user_id), remnant_id)
        )
        conn.commit()
        return cursor.rowcount > 0 # Agar o'zgargan bo'lsa True qaytaradi
    except Exception as e:
        print(f"❌ DB use_remnant error: {e}")
        return False
    finally:
        conn.close()

def restore_remnant(remnant_id):
    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        # Statusni 1 qilamiz, used_by ni NULL qilamiz
        cursor.execute(
            "UPDATE remnants SET status = 1, used_by = NULL, updated_at = NOW() WHERE id = %s",
            (remnant_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ DB restore error: {e}")
        return False
    finally:
        conn.close()

def get_remnant_details(remnant_id):
    """ID bo'yicha to'liq ma'lumotni olish"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM remnants WHERE id = %s", (remnant_id,))
        return cursor.fetchone()
    finally: conn.close()

def smart_search(query_text, min_w=0, min_h=0, is_flexible=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Asosiy so'rov: material nomi va status bo'yicha
        sql = "SELECT * FROM remnants WHERE (material ILIKE %s OR category ILIKE %s) AND status = 1"
        params = [f"%{query_text}%", f"%{query_text}%"]

        # Agar foydalanuvchi detal kessa bo'ladiganini so'ragan bo'lsa
        if min_w > 0 and min_h > 0:
            if is_flexible:
                # Yaqin oraliqda qidirish (±100 mm farq bilan yoki kattaroq)
                sql += " AND width >= %s AND height >= %s"
                params.extend([min_w - 50, min_h - 50])
            else:
                # Aniq detal chiqishi kerak bo'lgan holat
                sql += " AND ((width >= %s AND height >= %s) OR (width >= %s AND height >= %s))"
                params.extend([min_w, min_h, min_h, min_w]) # Eni va bo'yi almashishi mumkin

        sql += " ORDER BY width * height ASC LIMIT 10" # Eng kichik mos keladigandan boshlab
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally: conn.close()
