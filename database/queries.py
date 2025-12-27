import re
from datetime import datetime
from database.connection import get_db_connection
from psycopg2.extras import RealDictCursor

def advanced_bot_search(query_text):
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # 1. Tozalash va statusni aniqlash
        query_text = query_text.lower().strip()
        is_used = "ishlatilgan" in query_text
        status = 0 if is_used else 1
        clean_text = query_text.replace("ishlatilgan", "").strip()

        # 2. ID bo'yicha qidiruv (#75 yoki shunchaki 75)
        if clean_text.startswith('#') or (clean_text.isdigit() and len(clean_text) < 6):
            r_id = clean_text.replace('#', '')
            cursor.execute("SELECT * FROM remnants WHERE id = %s", (int(r_id),))
            return cursor.fetchall()

        # 3. O'lchamlarni ajratib olish (Masalan: 200x500 yoki 200*500)
        dimensions = re.findall(r'(\d+)\s*[x*×]\s*(\d+)', clean_text)
        
        sql = "SELECT * FROM remnants WHERE status = %s"
        params = [status]

        if dimensions:
            w, h = dimensions[0]
            # Eni va bo'yini aylantirib qidirish (200x500 so'rasa 500x200 ni ham topadi)
            sql += " AND ((width >= %s AND height >= %s) OR (width >= %s AND height >= %s))"
            params.extend([int(w), int(h), int(h), int(w)])
            # O'lchamdan qolgan so'zlarni (rang, material) tozalash
            clean_text = re.sub(r'(\d+)\s*[x*×]\s*(\d+)', '', clean_text).strip()

        # 4. Qolgan so'zlar (Material yoki Kategoriya) bo'yicha qidiruv
        if clean_text:
            words = clean_text.split()
            for word in words:
                sql += " AND (material ILIKE %s OR category ILIKE %s OR origin_order ILIKE %s)"
                params.extend([f"%{word}%", f"%{word}%", f"%{word}%"])

        sql += " ORDER BY id DESC LIMIT 10"
        cursor.execute(sql, params)
        return cursor.fetchall()

    except Exception as e:
        print(f"❌ Search Error: {e}")
        return []
    finally:
        conn.close()
        

def search_remnants(query_text):
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        is_used_search = "ishlatilgan" in query_text.lower()
        status_filter = 0 if is_used_search else 1
        clean_query = query_text.lower().replace("ishlatilgan", "").strip()
        search_param = f"%{clean_query}%"
        
        # SQL: Aniq ustunlar tartibini belgilaymiz
        query = """
            SELECT id, category, material, width, height, qty, origin_order, location, status, created_by_user_id 
            FROM remnants 
            WHERE (material ILIKE %s OR category ILIKE %s OR CAST(id AS TEXT) ILIKE %s) 
            AND status = %s
            ORDER BY id DESC
        """
        cursor.execute(query, (search_param, search_param, search_param, status_filter))
        return cursor.fetchall()
    except Exception as e:
        print(f"SQL Error: {e}")
        return []
    finally:
        conn.close()

# Boshqa funksiyalarda ham status va ustunlar tartibini tekshirib oling


def get_used_remnants(user_id=None):
    """Ishlatilgan qoldiqlarni olish (Agar user_id berilsa, faqat o'zinikini)"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
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
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM remnants WHERE status = 1 ORDER BY id DESC")
        return cursor.fetchall()
    finally: conn.close()
        

# --- 2. DUBLIKATNI TEKSHIRISH ---
def check_duplicate(material, width, height, location):
    """Aynan bir xil o'lcham va materialdagi qoldiqni topish"""
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(cursor_factory=RealDictCursor)
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
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Avval eski sonini olamiz
        cursor.execute("SELECT qty FROM remnants WHERE id = %s", (remnant_id,))
        result = cursor.fetchone()
        if not result:
            return None
        old_qty = result['qty']
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
    cursor = conn.cursor(cursor_factory=RealDictCursor)
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
        result = cursor.fetchone()
        if not result:
            return None
        new_id = result['id']
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
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (str(user_id),))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute(
                "INSERT INTO users (user_id, full_name, username, can_search, can_add) VALUES (%s, %s, %s, 0, 0)",
                (str(user_id), full_name, username)
            )
            conn.commit()
            # Yangi yaratilgan userni qayta o'qib olamiz (RealDictCursor formatida)
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (str(user_id),))
            user = cursor.fetchone()
            return user
        return user
    finally:
        conn.close()

# --- 6. RUXSATLARNI YANGILASH (SYNC UCHUN) ---
def update_user_permission(user_id, status):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Agar user bazada bo'lsa yangilaydi, bo'lmasa qo'shadi
        query = """
            INSERT INTO users (user_id, can_search, can_add, can_edit, can_delete, can_checkout)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
            can_search = EXCLUDED.can_search,
            can_add = EXCLUDED.can_add,
            can_edit = EXCLUDED.can_edit,
            can_delete = EXCLUDED.can_delete,
            can_checkout = EXCLUDED.can_checkout;
        """
        # Hozircha hamma ruxsatni bir xil statusga o'tkazamiz
        cursor.execute(query, (user_id, status, status, status, status, status))
        conn.commit()
    except Exception as e:
        print(f"❌ User permission error: {e}")
    finally:
        conn.close()

# --- 7. SHEETDAN TAHRIRLANGANDA YANGILASH ---
def sync_remnant_from_sheet(row):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # 1. Ma'lumotlarni tozalash va listga o'tkazish
        r = [str(x).strip() if (x is not None and x != "") else None for x in row]
        while len(r) < 17: r.append(None)

        # 2. ID ni tekshirish (A ustun)
        raw_id = r[0].replace('#', '') if r[0] else None
        if not raw_id or not raw_id.isdigit():
            return 

        # 3. MA'LUMOT TURLARINI XAVFSIZ O'GIRISH (Safe Casting)
        def to_int(val):
            try:
                if not val: return None
                return int(float(str(val).replace(',', '.')))
            except: return None

        # SQL so'rovi (A-Q)
        query = """
            INSERT INTO remnants (
                id, category, material, width, height, qty, origin_order, location, 
                status, image_id, created_by_user_id, created_by_name, created_at, 
                used_by_user_id, used_by_name, used_for_order, used_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO UPDATE SET
                category = EXCLUDED.category,
                material = EXCLUDED.material,
                width = EXCLUDED.width,
                height = EXCLUDED.height,
                qty = EXCLUDED.qty,
                origin_order = EXCLUDED.origin_order,
                location = EXCLUDED.location,
                status = EXCLUDED.status,
                image_id = EXCLUDED.image_id,
                created_by_user_id = EXCLUDED.created_by_user_id,
                created_by_name = EXCLUDED.created_by_name,
                created_at = EXCLUDED.created_at,
                used_by_user_id = EXCLUDED.used_by_user_id,
                used_by_name = EXCLUDED.used_by_name,
                used_for_order = EXCLUDED.used_for_order,
                used_at = EXCLUDED.used_at,
                updated_at = NOW();
        """

        # Parametrlarni xavfsiz tayyorlash
        # Sizning logingizda 'Zamin Baraka' matni son kutgan joyga kelgan
        # Bu odatda r[10] (created_by_user_id) yoki r[13] (used_by_user_id) bo'ladi
        params = (
            int(raw_id),        # A: id
            r[1],               # B: category
            r[2],               # C: material
            to_int(r[3]),       # D: width
            to_int(r[4]),       # E: height
            to_int(r[5]),       # F: qty
            r[6],               # G: origin_order
            r[7],               # H: location
            to_int(r[8]) if r[8] else 1, # I: status
            r[9],               # J: image_id (Text)
            to_int(r[10]),      # K: created_by_user_id (Must be BIGINT)
            r[11],              # L: created_by_name (Text)
            r[12],              # M: created_at (Text)
            to_int(r[13]),      # N: used_by_user_id (Must be BIGINT)
            r[14],              # O: used_by_name (Text)
            r[15],              # P: used_for_order (Text)
            r[16]               # Q: used_at (Text)
        )

        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        print(f"⚠️ Row Sync Error (ID: {row[0]}): {e}")
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
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM remnants WHERE id = %s", (remnant_id,))
        return cursor.fetchone()
    finally: conn.close()

def smart_search(query, min_w=0, min_h=0, is_flexible=False):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Asosiy so'rov: material nomi va status bo'yicha
        sql = "SELECT * FROM remnants WHERE (material ILIKE %s OR category ILIKE %s) AND status = 1"
        params = [f"%{query}%", f"%{query}%"]

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



def advanced_search_db(keywords, min_w=0, min_h=0):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Faqat mavjud (status=1) qoldiqlarni olamiz
        sql = "SELECT * FROM remnants WHERE status = 1"
        params = []

        # 1. KALIT SO'ZLAR BO'YICHA (ENG MUHIM QISM)
        if keywords:
            conditions = []
            for word in keywords:
                # Agar so'z '#' bilan boshlansa (masalan #25), ID bo'yicha qidiramiz
                if word.startswith('#') and word[1:].isdigit():
                    conditions.append("id = %s")
                    params.append(int(word[1:]))
                else:
                    # Qolgan barcha holatda: Material, Kategoriya, Lokatsiya VA BUYURTMA RAQAMI
                    # Mana shu yerga 'origin_order' qo'shdik!
                    conditions.append("""(
                        material ILIKE %s OR 
                        category ILIKE %s OR 
                        location ILIKE %s OR 
                        origin_order ILIKE %s
                    )""")
                    # 4 ta joyga bir xil so'zni qo'yamiz
                    like_word = f"%{word}%"
                    params.extend([like_word, like_word, like_word, like_word])
            
            if conditions:
                sql += " AND (" + " AND ".join(conditions) + ")"

        # 2. O'LCHAM BO'YICHA (Aylantirib qidirish)
        # 200x500 so'rasa, 500x200 ni ham topadi
        if min_w > 0 and min_h > 0:
            sql += """ AND (
                (width >= %s AND height >= %s) OR 
                (width >= %s AND height >= %s)
            )"""
            params.extend([min_w, min_h, min_h, min_w])

        cursor.execute(sql, params)
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ DB Search Error: {e}")
        return []
    finally:
        conn.close()
