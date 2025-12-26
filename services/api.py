from aiohttp import web
import json
import database.queries as db
from config import ADMIN_ID

# API: Barcha qoldiqlarni olish (Filterlar bilan)
async def get_remnants(request):
    try:
        # URL parametrlarini o'qiymiz
        params = request.rel_url.query
        user_id = params.get('user_id')
        filter_type = params.get('type', 'all') # all, mine, used
        category = params.get('category')
        
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM remnants WHERE 1=1"
        args = []

        if filter_type == 'mine':
            sql += " AND user_id = %s AND status = 1"
            args.append(user_id)
        elif filter_type == 'used':
            sql += " AND status = 0 AND used_by = %s"
            args.append(user_id)
        else: # 'all'
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
        return web.json_response({'error': str(e)}, status=500)

# API: Qoldiqni ishlatish (Olish)
async def use_remnant(request):
    data = await request.json()
    r_id = data.get('id')
    user_id = data.get('user_id')
    
    # Bazada update qilish
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE remnants SET status=0, used_by=%s WHERE id=%s", (user_id, r_id))
    conn.commit()
    conn.close()
    
    return web.json_response({'status': 'ok'})

# API: Qoldiq qo'shish
async def add_remnant(request):
    data = await request.json()
    # Bu yerda db.add_remnant chaqiriladi (soddalashtirilgan)
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO remnants (category, material, width, height, qty, origin_order, location, user_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
        """, (data['category'], data['material'], data['width'], data['height'], data['qty'], data['order'], data['location'], data['user_id']))
        conn.commit()
        conn.close()
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

# API: Kategoriyalarni olish (Filter uchun)
async def get_categories(request):
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM remnants WHERE status=1")
    cats = [row['category'] for row in cur.fetchall()]
    conn.close()
    return web.json_response(cats)
