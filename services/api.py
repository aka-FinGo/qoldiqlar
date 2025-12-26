from aiohttp import web
import json
import database.queries as db
from config import ADMIN_ID

# --- YORDAMCHI: SONLARNI FORMATLASH ---
def format_currency(value):
    return f"{value:,}".replace(",", " ")

# --- 1. GET (Olish) ---
async def get_remnants(request):
    try:
        params = request.rel_url.query
        user_id = params.get('user_id')
        filter_type = params.get('type', 'all')
        category = params.get('category')
        
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # Asosiy Query
        sql = "SELECT * FROM remnants WHERE 1=1"
        args = []

        if filter_type == 'mine':
            # Profil: Faqat o'zim qo'shganlar (status farqi yo'q, hammasi ko'rinsin)
            sql += " AND user_id = %s"
            args.append(user_id)
        elif filter_type == 'used':
            # Profil: Men ishlatganlarim
            sql += " AND status = 0 AND used_by = %s"
            args.append(user_id)
        else: # 'all'
            # Bosh sahifa: Faqat omborda borlar (status=1)
            sql += " AND status = 1"

        if category and category != 'all':
            sql += " AND category = %s"
            args.append(category)

        sql += " ORDER BY id DESC"
        
        cursor.execute(sql, args)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        
        return web.json_response(results)
    except Exception as e:
        # Xato bo'lsa ham JSON qaytarish kerak, lekin error flag bilan
        return web.json_response({'error': str(e)}, status=500)

async def get_categories(request):
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()
        # Faqat bor narsalarni kategoriyasini olamiz
        cur.execute("SELECT DISTINCT category FROM remnants WHERE status=1 ORDER BY category")
        cats = [row[0] for row in cur.fetchall()]
        conn.close()
        return web.json_response(cats)
    except Exception as e:
        return web.json_response([]) # Xato bo'lsa bo'sh ro'yxat

async def check_is_admin(request):
    try:
        user_id = request.rel_url.query.get('user_id')
        is_admin = str(user_id) == str(ADMIN_ID)
        return web.json_response({'is_admin': is_admin})
    except:
        return web.json_response({'is_admin': False})

# --- 2. POST (O'zgartirish) ---
async def use_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE remnants SET status=0, used_by=%s WHERE id=%s", (data['user_id'], data['id']))
        conn.commit()
        conn.close()
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def add_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO remnants (category, material, width, height, qty, origin_order, location, user_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
        """, (data['category'], data['material'], int(data['width']), int(data['height']), int(data['qty']), data.get('order',''), data.get('location',''), data['user_id']))
        conn.commit()
        conn.close()
        return web.json_response({'status': 'ok'})
    except Exception as e:
        print(f"ADD ERROR: {e}") # Logga yozish
        return web.json_response({'error': str(e)}, status=500)

async def edit_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE remnants 
            SET category=%s, material=%s, width=%s, height=%s, qty=%s, origin_order=%s, location=%s
            WHERE id=%s
        """, (data['category'], data['material'], int(data['width']), int(data['height']), int(data['qty']), data.get('order',''), data.get('location',''), data['id']))
        conn.commit()
        conn.close()
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def delete_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM remnants WHERE id=%s", (data['id'],))
        conn.commit()
        conn.close()
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)
