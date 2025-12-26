import database.queries as db

def perform_smart_search(ai_params):
    """
    AI parametrlari asosida aqlli qidiruv.
    ai_params misoli: 
    {
        "keywords": ["oq", "ldsp"], 
        "min_w": 200, 
        "min_h": 500, 
        "fuzzy": True
    }
    """
    keywords = ai_params.get('keywords', [])
    min_w = ai_params.get('min_w', 0)
    min_h = ai_params.get('min_h', 0)
    
    # 1. Agar o'lcham berilgan bo'lsa, DATABASE darajasida filtrlaymiz
    # Bu token sarfini 0 ga tushiradi, chunki AI bazani o'qimaydi.
    results = db.advanced_search_db(keywords, min_w, min_h)
    
    # 2. Natijalarni saralash (eng kichik mos keladiganidan boshlab)
    # Maqsad: Katta listni kesib isrof qilmaslik uchun, eng yaqin o'lchamni taklif qilish.
    if min_w > 0 and min_h > 0:
        # Yuzasi bo'yicha saralash (kichikroq qoldiq oldin chiqsin)
        results.sort(key=lambda x: x['width'] * x['height'])
    
    return results
