from aiohttp import web
import json
import database.queries as db
from config import ADMIN_ID
from services.gsheets import sync_new_remnant 

# --- GET: Qoldiqlarni olish ---
async def get_remnants(request):
    try:
        params = request.rel_url.query
        user_id = params.get('user_id')
        filter_type = params.get('type', 'all')
        category = params.get('category')
        
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # SQL: Ustun nomlarini 'AS' orqali Frontendga moslaymiz
        sql = """
            SELECT id, category, material, width, height, qty, 
                   origin_order, location, status, 
                   created_by_user_id AS user_id 
            FROM remnants WHERE 1=1
        """
        args = []

        if filter_type == 'mine':
            sql += " AND created_by_user_id = %s"
            args.append(user_id)
        elif filter_type == 'used':
            sql += " AND status = 0 AND used_by_user_id = %s"
            args.append(user_id)
        else:
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
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM remnants WHERE status = 1")
        cats = [row[0] for row in cur.fetchall() if row[0]]
        conn.close()
        return web.json_response(cats)
    except:
        return web.json_response([])

async def check_is_admin(request):
    user_id = request.rel_url.query.get('user_id')
    return web.json_response({'is_admin': str(user_id) == str(ADMIN_ID)})

# --- POST: Amallar (ImportError bermasligi uchun nomlar aniq) ---

async def use_remnant(request): # Nomiga e'tibor bering!
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE remnants SET status=0, used_by_user_id=%s, used_at=NOW() WHERE id=%s", 
                   (data['user_id'], data['id']))
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
            INSERT INTO remnants (category, material, width, height, qty, origin_order, location, created_by_user_id, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, NOW()) RETURNING id
        """, (data['category'], data['material'], int(data['width']), int(data['height']), 
              int(data['qty']), data.get('order',''), data.get('location',''), data['user_id']))
        new_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        
        # GSheets sync
        try:
            sync_new_remnant({'id': new_id, **data})
        except: pass
        
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def edit_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE remnants SET category=%s, material=%s, width=%s, height=%s, qty=%s, origin_order=%s, location=%s, updated_at=NOW()
            WHERE id=%s
        """, (data['category'], data['material'], int(data['width']), int(data['height']), 
              int(data['qty']), data.get('order',''), data.get('location',''), data['id']))
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
