from aiohttp import web
import database.queries as db
from config import ADMIN_ID
from services.gsheets import sync_new_remnant 
import logging

logger = logging.getLogger(__name__)
# --- 1. Qoldiqlarni olish (Indeksli mapping - Xato bermaydi) ---
async def get_remnants(request):
    conn = None
    try:
        user_id = request.rel_url.query.get('user_id')
        filter_type = request.rel_url.query.get('type', 'all')
        
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # Bazadagi haqiqiy ustun nomlari
        sql = "SELECT id, category, material, width, height, qty, origin_order, location, status, created_by_user_id FROM remnants WHERE 1=1"
        
        if filter_type == 'mine':
            sql += f" AND created_by_user_id = {user_id}"
        elif filter_type == 'used':
            sql += f" AND status = 0 AND used_by_user_id = {user_id}"
        else:
            sql += " AND status = 1"
            
        sql += " ORDER BY id DESC"
        cursor.execute(sql)
        rows = cursor.fetchall()

        results = []
        for r in rows:
            # Rivojlangan tekshiruv: Ma'lumot borligiga ishonch hosil qilish
            if len(r) >= 10:
                results.append({
                    "id": r[0],
                    "category": str(r[1] or ""),
                    "material": str(r[2] or ""),
                    "width": int(r[3] or 0),
                    "height": int(r[4] or 0),
                    "qty": int(r[5] or 0),
                    "order": str(r[6] or ""),
                    "location": str(r[7] or ""),
                    "status": int(r[8] or 1),
                    "user_id": str(r[9] or "")
                })
        
        return web.json_response(results)
    except Exception as e:
        logger.error(f"FATAL API ERROR: {e}")
        return web.json_response({"error": str(e)}, status=500)
    finally:
        if conn: conn.close()

# get_categories, add_remnant, edit_remnant funksiyalari o'zgarishsiz qolsin

# --- 2. Kategoriyalar ---
async def get_categories(request):
    conn = None
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM remnants WHERE status = 1")
        cats = [row[0] for row in cur.fetchall() if row[0]]
        return web.json_response(cats)
    except:
        return web.json_response([])
    finally:
        if conn: conn.close()

# --- 3. Ishlatish (Nomi main.py dagi importga mos) ---
async def use_remnant(request):
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

# --- 4. Qo'shish ---
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
        try: sync_new_remnant({'id': new_id, **data})
        except: pass
        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

# --- 5. Tahrirlash ---
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

# --- 6. O'chirish ---
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

# --- 7. Admin tekshiruvi ---
async def check_is_admin(request):
    user_id = request.rel_url.query.get('user_id')
    return web.json_response({'is_admin': str(user_id) == str(ADMIN_ID)})
