from aiohttp import web
import database.queries as db
from config import ADMIN_ID
from services.gsheets import sync_new_remnant 

async def get_remnants(request):
    try:
        params = request.rel_url.query
        user_id = params.get('user_id')
        filter_type = params.get('type', 'all')
        category = params.get('category')
        
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # Barcha ustunlarni tanlaymiz
        sql = "SELECT * FROM remnants WHERE 1=1"
        args = []

        if filter_type == 'mine':
            sql += " AND created_by_user_id = %s"
            args.append(user_id)
        elif filter_type == 'used':
            sql += " AND status = 0 AND used_by_user_id = %s"
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

async def get_categories(request):
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()
        # Bazadagi 'category' ustunidan barcha nomlarni olamiz
        cur.execute("SELECT DISTINCT category FROM remnants WHERE status=1")
        cats = [row[0] for row in cur.fetchall() if row[0]]
        conn.close()
        return web.json_response(cats)
    except:
        return web.json_response([])

# Tahrirlash funksiyasi (SQL ustunlariga moslangan)
async def edit_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE remnants 
            SET category=%s, material=%s, width=%s, height=%s, qty=%s, 
                origin_order=%s, location=%s, updated_at=NOW()
            WHERE id=%s
        """, (data['category'], data['material'], int(data['width']), int(data['height']), 
              int(data['qty']), data.get('order',''), data.get('location',''), data['id']))
        conn.commit()
        conn.close()
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)
