from aiohttp import web
import psycopg2
from psycopg2.extras import RealDictCursor  # <--- MANA SHU QATORNI QO'SHING
import database.queries as db
from config import ADMIN_ID
from services.gsheets import sync_new_remnant 
import logging

logger = logging.getLogger(__name__)
# --- 1. Qoldiqlarni olish (Indeksli mapping - Xato bermaydi) ---
from aiohttp import web
import database.queries as db
from config import ADMIN_ID
import logging

logger = logging.getLogger(__name__)

async def get_remnants(request):
    conn = None
    try:
        params = request.rel_url.query
        user_id = params.get('user_id')
        filter_type = params.get('type', 'all')
        category = params.get('category')
        
        conn = db.get_db_connection()
        # Kursor ochishda RealDictCursor ishlatamiz
        cursor = conn.cursor(cursor_factory=RealDictCursor) 
        
        sql = "SELECT * FROM remnants WHERE 1=1"
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
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            # Endi r[0] emas, r['id'] ko'rinishida yozamiz
            results.append({
                "id": r['id'],
                "category": str(r['category'] or ""),
                "material": str(r['material'] or ""),
                "width": int(r['width'] or 0),
                "height": int(r['height'] or 0),
                "qty": int(r['qty'] or 0),
                "origin_order": str(r['origin_order'] or ""),
                "location": str(r['location'] or ""),
                "status": int(r['status'] or 1),
                "user_id": str(r['created_by_user_id'] or "")
            })
        
        return web.json_response(results)
    except Exception as e:
        logger.error(f"FATAL API ERROR: {str(e)}")
        return web.json_response({"error": str(e)}, status=500)
    finally:
        if conn:
            conn.close()

# Boshqa admin funksiyalar (use, edit, delete) o'zgarishsiz qolishi mumkin 
# yoki xuddi shu indeksli mantiqqa o'tkazilishi kerak.

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
        # 1. Bazada yangilash
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE remnants SET status=0, used_by_user_id=%s, used_at=NOW() WHERE id=%s", 
                   (data['user_id'], data['id']))
        conn.commit()
        conn.close()

        # 2. Sheetda ham N-Q ustunlarini to'ldirish
        try:
            from services.gsheets import mark_as_used_in_sheet
            # Mini appdan user_name va order_for ma'lumotlarini ham yuborish kerak
            mark_as_used_in_sheet(data['id'], data['user_id'], data.get('user_name', 'Noma\'lum'), data.get('order_for', '-'))
        except: pass

        return web.json_response({'status': 'ok'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)
        
# --- 4. Qo'shish ---
# --- 4. Yangi qo'shish ---
async def add_remnant(request):
    try:
        data = await request.json()
        conn = db.get_db_connection()
        cur = conn.cursor()
        
        # 1. Bazaga saqlash
        cur.execute("""
            INSERT INTO remnants (category, material, width, height, qty, origin_order, location, created_by_user_id, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, NOW()) RETURNING id
        """, (data['category'], data['material'], int(data['width']), int(data['height']), 
              int(data['qty']), data.get('order',''), data.get('location',''), data['user_id']))
        
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        # 2. GSheets-ga yuborish (Sizdagi IndentationError shu yerda edi)
        try:
            # Bazadan olingan yangi ID ni data obyektiga qo'shamiz
            data['id'] = new_id  
            sync_new_remnant(data)
            logger.info(f"✅ Yangi qoldiq GSheets-ga qo'shildi: #{new_id}")
        except Exception as e:
            logger.error(f"❌ GSheets-ga yozishda xato: {str(e)}")
            # GSheets-da xato bo'lsa ham foydalanuvchiga 'ok' qaytaramiz, 
            # chunki bazaga yozib bo'lindi.

        return web.json_response({'status': 'ok', 'id': new_id})

    except Exception as e:
        logger.error(f"❌ ADD_REMNANT ERROR: {str(e)}")
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
