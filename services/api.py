from aiohttp import web
import json
import database.queries as db
from config import ADMIN_ID
from services.gsheets import sync_new_remnant 
import logging

# Loglarni sozlash
logger = logging.getLogger(__name__)

# --- 1. GET: Qoldiqlarni olish (Kafolatlangan mantiq) ---
async def get_remnants(request):
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # Eng oddiy so'rov
        cursor.execute("SELECT * FROM remnants LIMIT 1")
        
        row = cursor.fetchone() # Bitta qatorni olamiz
        desc = cursor.description # Ustun nomlari
        
        conn.close()

        # Debug ma'lumotini shakllantiramiz
        debug_info = {
            "database_raw_row": str(row), # Bazadan kelgan asl tuple
            "database_columns": [d[0] for d in desc], # Ustun nomlari
            "test_manual_mapping": {}
        }

        # Agar ma'lumot bo'lsa, qo'lda mapping qilamiz
        if row and desc:
            for i in range(len(desc)):
                debug_info["test_manual_mapping"][desc[i][0]] = row[i]

        return web.json_response(debug_info)
    except Exception as e:
        return web.json_response({"debug_error": str(e)})


# --- 2. GET: Kategoriyalarni olish ---
async def get_categories(request):
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM remnants WHERE status = 1")
        cats = [row[0] for row in cur.fetchall() if row[0]]
        conn.close()
        return web.json_response(cats)
    except Exception as e:
        return web.json_response([])

# --- 3. GET: Adminlikni tekshirish ---
async def check_is_admin(request):
    user_id = request.rel_url.query.get('user_id')
    is_admin = str(user_id) == str(ADMIN_ID)
    return web.json_response({'is_admin': is_admin})

# --- 4. POST: Qoldiqdan foydalanish (Ishlatish) ---
async def use_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        # Statusni 0 qilamiz va kim ishlatganini yozamiz
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

# --- 5. POST: Yangi qoldiq qo'shish ---
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
        
        # GSheets bilan sinxronlash
        try:
            sync_new_remnant({'id': new_id, **data})
        except Exception as e:
            logger.error(f"GSheets Sync Error: {e}")
            
        return web.json_response({'status': 'ok', 'id': new_id})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

# --- 6. POST: Tahrirlash ---
async def edit_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE remnants 
            SET category=%s, material=%s, width=%s, height=%s, qty=%s, origin_order=%s, location=%s, updated_at=NOW()
            WHERE id=%s
        """, (data['category'], data['material'], int(data['width']), int(data['height']), 
              int(data['qty']), data.get('order',''), data.get('location',''), data['id']))
        conn.commit()
        conn.close()
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

# --- 7. POST: O'chirish ---
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
