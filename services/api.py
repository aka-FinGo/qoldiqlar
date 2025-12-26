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
        
        # SQL: Bazadagi haqiqiy ustun nomlari
        sql = "SELECT id, category, material, width, height, qty, origin_order, location, status, created_by_user_id FROM remnants WHERE 1=1"
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
        cur.execute("SELECT DISTINCT category FROM remnants WHERE status=1")
        cats = [row[0] for row in cur.fetchall() if row[0]]
        conn.close()
        return web.json_response(cats)
    except:
        return web.json_response([])

async def add_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        # RETURNING id - yangi qo'shilgan qator ID sini olish uchun
        cur.execute("""
            INSERT INTO remnants (category, material, width, height, qty, origin_order, location, created_by_user_id, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, NOW())
            RETURNING id
        """, (data['category'], data['material'], int(data['width']), int(data['height']), int(data['qty']), data.get('order',''), data.get('location',''), data['user_id']))
        
        new_id = cur.fetchone()[0]
        conn.commit()
        conn.close()

        # Sheetga yozish qismi
        try:
            sheet_data = {
                'id': new_id, 'category': data['category'], 'material': data['material'],
                'width': data['width'], 'height': data['height'], 'qty': data['qty'],
                'order': data.get('order',''), 'location': data.get('location',''),
                'user_id': data['user_id'], 'user_name': 'MiniApp'
            }
            sync_new_remnant(sheet_data)
        except: pass

        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)
