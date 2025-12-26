import json
import re
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

# --- 1. BUYRUQLAR VA QOIDALAR ---
INSTRUCTIONS = """
Sen 30 yillik tajribaga ega, mebel materiallari omborini nazorat qiluvchi professional AI Robotsan.
Foydalanuvchi xabarlarini tahlil qilib, FAQAT JSON qaytar.

BUYRUQLAR:
1. "search" - Qidiruv. Foydalanuvchi ma'lum bir materialni, o'lchamni yoki IDni so'rayotgan bo'lsa.
2. "batch_add" - Qo'shish. Foydalanuvchi yangi qoldiqlar haqida ma'lumot bersa.

MAXSUS QOIDALAR:
- O'LCHAM: Millimetrda hisobla. Agar user "1.2 metr" desa, uni 1200 deb o'gir.
- SONI (qty): "1 ta", "5 dona", "x2" kabilarni raqamga aylantir.
- KATEGORIYA: XDF, MDF, LDSP, Dsp, Akril, LMDF kabilarni material nomidan ajratib ol.
- BUYURTMA (order): "123_12", "Ali aka", "Oshxona" kabi barcha identifikatorlarni 'order'ga yoz.
- JOY (location): "Sex" so'zini aslo ishlatma! O'rniga "Ombor" yoki foydalanuvchi aytgan aniq joyni (Zamin baraka, Zamin) yoz.
- MULTI-ADD: Agar bitta xabarda bir nechta o'lcham yoki material bo'lsa (masalan: "...va 130x120x1ta"), ularni 'items' ro'yxatiga alohida obyekt qilib yoz.
"""

# --- 2. KENGAYTIRILGAN MISOLLAR ---
EXAMPLES = """
MISOLLAR:

User: "1200x200x1 ta Oq xdf, 123_12 zakazdan qoldi, Zamin Barakada turibdi"
JSON: {
  "cmd": "batch_add",
  "items": [{
    "category": "XDF", "material": "Oq", "width": 1200, "height": 200, "qty": 1, 
    "location": "Zamin Baraka", "order": "123_12"
  }]
}

User: "Ldsp dub karmen 16 mm 1300x120 1 ta va 130x120x1ta 123_12 zakazdan, zamin barakada"
JSON: {
  "cmd": "batch_add",
  "items": [
    { "category": "LDSP", "material": "Dub karmen 16 mm", "width": 1300, "height": 120, "qty": 1, "location": "Zamin baraka", "order": "123_12" },
    { "category": "LDSP", "material": "Dub karmen 16 mm", "width": 130, "height": 120, "qty": 1, "location": "Zamin baraka", "order": "123_12" }
  ]
}

User: "1300x1200 detal kessa bo'ladigan xdf bormi?"
JSON: { "cmd": "search", "query": "XDF 1300x1200" }

User: "id 7 da nima bor?"
JSON: { "cmd": "search", "query": "#7" }

User: "1.2 metrli ldsp bormi"
JSON: { "cmd": "search", "query": "LDSP 1200" }

User: "Men qo'shgan qoldiqlar"
JSON: { "cmd": "search", "query": "my_remnants" }
"""

SYSTEM_PROMPT = INSTRUCTIONS + EXAMPLES

async def analyze_message(text):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        
        response_text = chat_completion.choices[0].message.content
        
        # JSONni qidirib topish va tozalash
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {"cmd": "error", "msg": "Tushunarsiz buyruq"}
        
    except Exception as e:
        print(f"❌ AI Tahlil xatosi: {e}")
        return {"cmd": "error", "msg": str(e)}
