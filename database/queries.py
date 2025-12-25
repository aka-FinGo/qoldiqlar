from database.connection import get_db_connection
from services.utils import normalize_text

# --- 1. QO'SHISH (ADD) ---
def add_remnant(category, material, width, height, qty, order, location, user_id, user_name):
    conn = get_db_connection()
    if not conn: return None
    
    cursor = conn.cursor()
    
    # Matnni tozalaymiz (Lotinlashtirish)
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
    # User "Оқ" yozsa ham "oq" qilib qidiramiz
    clean_query = normalize_text(query_text)
    
    try:
        sql = """
        SELECT id, material, width, height, qty, location, origin_order 
        FROM remnants 
        WHERE (material ILIKE %s OR category ILIKE %s) 
        AND status = 1
        ORDER BY id DESC LIMIT 10
        """
        # % belgisi matn ichidan qidirish uchun kerak
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
        
    else: # Hamma mavjudlari
        where_clause = " WHERE status = 1"
        order_by = " ORDER BY id DESC"

    full_query = base_query + where_clause + order_by + " LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    try:
        cursor.execute(full_query, tuple(params))
        return cursor.fetchall()
    finally:
        conn.close()
