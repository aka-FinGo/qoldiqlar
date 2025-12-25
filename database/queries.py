from database.connection import get_db_connection
from services.utils import normalize_text

# --- 1. QO'SHISH (ADD) ---
def add_remnant(category, material, width, height, qty, order, location, user_id, user_name):
    conn = get_db_connection()
    if not conn: return None
    
    cursor = conn.cursor()
    
    # Matnni tozalash va lotinlashtirish
    clean_mat = normalize_text(material)
    clean_cat = normalize_text(category)
    
    try:
        query = """
        INSERT INTO remnants 
        (category, material, width, height, qty, origin_order, location, created_by_user_id, created_by_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """
        cursor.execute(query, (clean_cat, clean_mat, width, height, qty, order, location, user_id, user_name))
        new_id = cursor.fetchone()['id']
        conn.commit()
        return new_id
    except Exception as e:
        print(f"Xatolik (Add): {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

# --- 2. QIDIRISH (SEARCH) ---
def search_remnants(query_text):
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor()
    clean_query = normalize_text(query_text)
    
    try:
        sql = """
        SELECT id, material, width, height, qty, location, origin_order 
        FROM remnants 
        WHERE (material ILIKE %s OR category ILIKE %s) 
        AND status = 1
        ORDER BY id DESC LIMIT 10
        """
        search_term = f"%{clean_query}%"
        cursor.execute(sql, (search_term, search_term))
        return cursor.fetchall()
    except Exception as e:
        print(f"Xatolik (Search): {e}")
        return []
    finally:
        conn.close()

# --- 3. RO'YXAT (LIST) ---
def get_list(filter_type, user_id=None, limit=10, offset=0):
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor()
    
    base_query = "SELECT id, material, width, height, qty, location, status FROM remnants"
    params = []
    
    if filter_type == 'my_added':
        where_clause = " WHERE created_by_user_id = %s AND status = 1"
        params.append(user_id)
        order_by = " ORDER BY id DESC"
    elif filter_type == 'used':
        where_clause = " WHERE status = 0"
        order_by = " ORDER BY used_at DESC"
    else:
        where_clause = " WHERE status = 1"
        order_by = " ORDER BY id DESC"

    full_query = base_query + where_clause + order_by + " LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    try:
        cursor.execute(full_query, tuple(params))
        return cursor.fetchall()
    finally:
        conn.close()

# --- 4. USERNI TEKSHIRISH (WHITELIST TIZIMI) ---
def get_or_create_user(user_id, full_name, username):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    
    try:
        # 1. Userni bazadan qidiramiz
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        
        # 2. Agar user yo'q bo'lsa -> Yangi qo'shamiz (RUXSATSIZ)
        if not user:
            cursor.execute("""
                INSERT INTO users 
                (user_id, full_name, username, can_search, can_add, can_edit, can_delete, can_checkout)
                VALUES (%s, %s, %s, 0, 0, 0, 0, 0)
            """, (user_id, full_name, username))
            conn.commit()
            
            # Yangi user ekanligini bildirish uchun belgi qo'shamiz
            return {"user_id": user_id, "can_search": 0, "is_new": True}
            
        return user # Bor userni qaytaramiz (is_new bo'lmaydi)
        
    except Exception as e:
        print(f"User DB xatosi: {e}")
        return None
    finally:
        conn.close()
