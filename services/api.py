from aiohttp import web
import json
import database.queries as db
from config import ADMIN_ID

# --- 1. MA'LUMOT OLISH (GET) ---

async def get_remnants(request):
    """Barcha qoldiqlarni filterlar bilan olish"""
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
            # Faqat o'zi qo'shgan va hali ishlatilmaganlar
            sql += " AND user_id = %s AND status = 1"
            args.append(user_id)
        elif filter_type == 'used':
            # O'zi ishlatganlar (tarix)
            sql += " AND status = 0 AND used_by = %s"
            args.append(user_id)
        else: # 'all'
            # Barcha mavjud qoldiqlar
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

async def get_categories(request):
    """Mavjud kategoriyalar ro'yxatini olish"""
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM remnants WHERE status=1")
        cats = [row['category'] for row in cur.fetchall()]
        conn.close()
        return web.json_response(cats)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def check_is_admin(request):
    """Foydalanuvchi Admin ekanligini tekshirish"""
    try:
        user_id = request.rel_url.query.get('user_id')
        # Configdagi ADMIN_ID bilan solishtiramiz
        is_admin = str(user_id) == str(ADMIN_ID)
        return web.json_response({'is_admin': is_admin})
    except Exception as e:
        return web.json_response({'is_admin': False, 'error': str(e)})

# --- 2. O'ZGARTIRISH VA QO'SHISH (POST) ---

async def use_remnant(request):
    """Qoldiqni ishlatish (Statusni 0 qilish)"""
    try:
        data = await request.json()
        r_id = data.get('id')
        user_id = data.get('user_id')
        
        conn = db.get_db_connection()
        cur = conn.cursor()
        # Status=0 va used_by=user_id qilib yangilaymiz
        cur.execute("UPDATE remnants SET status=0, used_by=%s WHERE id=%s", (user_id, r_id))
        conn.commit()
        conn.close()
        
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def add_remnant(request):
    """Yangi qoldiq qo'shish"""
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        
        # Bazaga INSERT qilish
        cur.execute("""
            INSERT INTO remnants (category, material, width, height, qty, origin_order, location, user_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
        """, (
            data.get('category'), 
            data.get('material'), 
            int(data.get('width')), 
            int(data.get('height')), 
            int(data.get('qty', 1)), 
            data.get('order', ''), 
            data.get('location', ''), 
            data.get('user_id'), 
        ))
        conn.commit()
        conn.close()
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def edit_remnant(request):
    """Mavjud qoldiqni tahrirlash (Admin panel uchun)"""
    try:
        data = await request.json()
        
        conn = db.get_db_connection()
        cur = conn.cursor()
        
        # Bazadagi ma'lumotni UPDATE qilish
        cur.execute("""
            UPDATE remnants 
            SET category=%s, material=%s, width=%s, height=%s, qty=%s, origin_order=%s, location=%s
            WHERE id=%s
        """, (
            data.get('category'), 
            data.get('material'), 
            int(data.get('width')), 
            int(data.get('height')), 
            int(data.get('qty')), 
            data.get('order', ''), 
            data.get('location', ''), 
            data.get('id')
        ))
        conn.commit()
        conn.close()
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def delete_remnant(request):
    """Qoldiqni butunlay o'chirish (Admin panel uchun)"""
    try:
        data = await request.json()
        r_id = data.get('id')
        
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM remnants WHERE id=%s", (r_id,))
        conn.commit()
        conn.close()
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)
