from aiohttp import web
import json
import database.queries as db
from config import ADMIN_ID
# Sheetga yozish uchun funksiyani chaqiramiz
from services.gsheets import sync_new_remnant 

# --- 1. GET (Olish) ---
async def get_remnants(request):
    try:
        params = request.rel_url.query
        user_id = params.get('user_id')
        filter_type = params.get('type', 'all')
        category = params.get('category')
        
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # SQL ni shunday yozamizki, Frontend tushunadigan 'user_id' qaytsin
        # created_by_user_id AS user_id degani - nomini o'zgartirib ber degani
        sql = """
            SELECT id, category, material, width, height, qty, origin_order, location, status, 
                   created_by_user_id AS user_id 
            FROM remnants WHERE 1=1
        """
        args = []

        if filter_type == 'mine':
            # Profil: O'zim qo'shganlar
            sql += " AND created_by_user_id = %s"
            args.append(user_id)
        elif filter_type == 'used':
            # Profil: Men ishlatganlarim
            sql += " AND status = 0 AND used_by_user_id = %s"
            args.append(user_id)
        else: # 'all'
            # Bosh sahifa
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
        # Faqat aktiv qoldiqlarning kategoriyalarini olamiz
        cur.execute("SELECT DISTINCT category FROM remnants WHERE status=1 ORDER BY category")
        cats = [row[0] for row in cur.fetchall()]
        conn.close()
        return web.json_response(cats)
    except Exception as e:
        return web.json_response([])

async def check_is_admin(request):
    try:
        user_id = request.rel_url.query.get('user_id')
        is_admin = str(user_id) == str(ADMIN_ID)
        return web.json_response({'is_admin': is_admin})
    except:
        return web.json_response({'is_admin': False})

# --- 2. POST (Amallar) ---

async def use_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        
        # Ishlatilganda used_by_user_id ga yozamiz
        cur.execute("""
            UPDATE remnants 
            SET status=0, used_by_user_id=%s, used_at=NOW() 
            WHERE id=%s
        """, (data['user_id'], data['id']))
        
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
        
        # 1. Bazaga yozish va ID ni qaytarib olish (RETURNING id)
        cur.execute("""
            INSERT INTO remnants (
                category, material, width, height, qty, 
                origin_order, location, created_by_user_id, status, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, NOW())
            RETURNING id
        """, (
            data['category'], 
            data['material'], 
            int(data['width']), 
            int(data['height']), 
            int(data['qty']), 
            data.get('order', ''), 
            data.get('location', ''), 
            data['user_id']
        ))
        
        new_id = cur.fetchone()[0] # Yangi ID ni oldik
        conn.commit()
        conn.close()

        # 2. Google Sheetsga ham yozamiz (Sinxronizatsiya)
        # sync_new_remnant funksiyasi dict kutadi
        sheet_data = {
            'id': new_id,
            'category': data['category'],
            'material': data['material'],
            'width': int(data['width']),
            'height': int(data['height']),
            'qty': int(data['qty']),
            'order': data.get('order', ''),
            'location': data.get('location', ''),
            'user_id': data['user_id'],
            'user_name': 'MiniApp User' # Ismni keyinchalik to'g'irlash mumkin
        }
        
        try:
            sync_new_remnant(sheet_data)
        except Exception as sheet_err:
            print(f"Sheet Sync Error: {sheet_err}")
            # Sheetga yozilmasa ham, dastur to'xtab qolmasin

        return web.json_response({'status': 'ok', 'new_id': new_id})
    except Exception as e:
        print(f"ADD ERROR: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def edit_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        
        # Tahrirlash
        cur.execute("""
            UPDATE remnants 
            SET category=%s, material=%s, width=%s, height=%s, qty=%s, 
                origin_order=%s, location=%s, updated_at=NOW()
            WHERE id=%s
        """, (
            data['category'], 
            data['material'], 
            int(data['width']), 
            int(data['height']), 
            int(data['qty']), 
            data.get('order', ''), 
            data.get('location', ''), 
            data['id']
        ))
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
