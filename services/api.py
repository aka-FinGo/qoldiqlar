from aiohttp import web
import database.queries as db
from config import ADMIN_ID
import logging

async def get_remnants(request):
    try:
        params = request.rel_url.query
        user_id = params.get('user_id')
        filter_type = params.get('type', 'all')
        category = params.get('category')
        
        conn = db.get_db_connection()
        # Kursorni ochamiz
        cursor = conn.cursor()
        
        # SQL: Bazangizdagi aniq ustun nomlari
        sql = """
            SELECT id, category, material, width, height, qty, 
                   origin_order, location, status, created_by_user_id 
            FROM remnants WHERE 1=1
        """
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
        
        # --- MUHIM: MA'LUMOTLARNI QAYTA ISHLASH ---
        # cursor.description - bu faqat ustun nomlari
        columns = [desc[0] for desc in cursor.description]
        
        # cursor.fetchall() - bu bazadagi haqiqiy QATORLAR
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            # zip orqali ('material', 'Oq') ko'rinishida juftlaymiz
            row_dict = {}
            for i in range(len(columns)):
                row_dict[columns[i]] = row[i]
            
            # Frontend kutayotgan user_id ni ham qo'shib qo'yamiz
            row_dict['user_id'] = row_dict.get('created_by_user_id')
            results.append(row_dict)
            
        conn.close()
        
        # Debug uchun log: haqiqatan ma'lumot keldimi?
        if results:
            logging.info(f"DEBUG: Birinchi qator ma'lumoti: {results[0]}")

        return web.json_response(results)
        
    except Exception as e:
        logging.error(f"API ERROR: {str(e)}")
        return web.json_response({'error': str(e)}, status=500)

# Qolgan funksiyalar (get_categories, add_remnant va h.k.) o'zgarishsiz qolsin
