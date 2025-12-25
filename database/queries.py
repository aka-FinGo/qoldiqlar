from database.connection import get_db_connection

def add_remnant(category, material, width, height, qty, order, location, user_id, user_name):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        # 1. Dublikatni tekshirish (Material, Bo'yi, Eni va Joylashuvi bir xil bo'lsa)
        check_query = """
            SELECT id, qty FROM remnants 
            WHERE material = %s AND width = %s AND height = %s AND location = %s AND status = 1
            LIMIT 1;
        """
        cursor.execute(check_query, (material, width, height, location))
        existing = cursor.fetchone()

        if existing:
            # Mavjud bo'lsa - SONINI OSHIRAMIZ
            new_qty = existing['qty'] + qty
            update_query = "UPDATE remnants SET qty = %s WHERE id = %s"
            cursor.execute(update_query, (new_qty, existing['id']))
            conn.commit()
            return f"upd_{existing['id']}" # Yangilanganini bildirish uchun
        else:
            # Yo'q bo'lsa - YANGI QO'SHAMIZ
            query = """INSERT INTO remnants (category, material, width, height, qty, origin_order, location, created_by_user_id, created_by_name)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;"""
            cursor.execute(query, (category, material, width, height, qty, order, location, user_id, user_name))
            new_id = cursor.fetchone()['id']
            conn.commit()
            return new_id
    except: return None
    finally: conn.close()


def get_or_create_user(user_id, full_name, username):
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.execute("INSERT INTO users (user_id, full_name, username, can_search, can_add) VALUES (%s, %s, %s, 0, 0)", (user_id, full_name, username))
            conn.commit()
            return {"user_id": user_id, "can_search": 0, "is_new": True}
        return user
    finally: conn.close()

def update_user_permission(user_id, can_search):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET can_search = %s, can_add = %s WHERE user_id = %s", (can_search, can_search, str(user_id)))
        conn.commit()
    finally: conn.close()

def sync_remnant_from_sheet(remnant_id, material, width, height, qty, location, status):
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    try:
        clean_id = int(str(remnant_id).replace('#', ''))
        cursor.execute("UPDATE remnants SET material=%s, width=%s, height=%s, qty=%s, location=%s, status=%s WHERE id=%s",
                       (material, width, height, qty, location, status, clean_id))
        conn.commit()
    finally: conn.close()
