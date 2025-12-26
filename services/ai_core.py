import json
import re
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

# --- 1. KOMPLEKS PROMPT (30 yillik tajribaga asoslangan) ---
INSTRUCTIONS = """
Sen 30 yillik tajribaga ega, mebel materiallari omborini nazorat qiluvchi professional AI Robotsan.
Foydalanuvchi xabarlarini tahlil qilib, FAQAT JSON qaytar.

BUYRUQLAR:
1. "search" - Qidiruv. Material, o'lcham, ID yoki foydalanuvchi tarixini so'raganda.
2. "batch_add" - Qo'shish. Yangi qoldiqlar haqida ma'lumot berilganda.

QOIDALAR:
- O'LCHAM: Millimetrda hisobla (1.2 metr = 1200). "Uzunlik x Eni" formatida ajrat.
- MATERIAL: Kategoriya (XDF, LDSP, MDF, Akril) va rangini (Oq, Dub karmen) aniq ajrat.
- SONI: "x2", "3ta", "5 dona" kabilarni raqamga aylantir. Default=1.
- BUYURTMA (order): "123_12", "№50", "Ali aka zakazi" kabi identifikatorlarni ajrat.
- LOKATSIYA VA IZOH (location): O'lcham, material va zakaz raqamidan tashqari barcha so'zlarni (joyi, holati, sababi, brak ekanligi) bitta matn qilib 'location' maydoniga jamla. 
  * "Sex" so'zini ishlatma, o'rniga "Ombor" yoki user aytgan joyni yoz.
  * Masalan: "Zamin barakada, brak chiqdi, chekkasi urilgan" -> hammasi 'location'ga.
"""

# --- 2. KENGAYTIRILGAN MISOLLAR (EXAMPLES) ---
EXAMPLES = """
MISOLLAR:

User: "1500x1500x1TA xdf oq, Zamin barakada turibdi, 123_12 dan zakazdan qoldi, chekkasi urilgan brak"
JSON: {
  "cmd": "batch_add",
  "items": [{
    "category": "XDF", "material": "Oq", "width": 1500, "height": 1500, "qty": 1, 
    "order": "123_12", "location": "Zamin baraka, zakazdan qoldi, chekkasi urilgan brak"
  }]
}

User: "Ldsp dub karmen 16 mm 1300x120 1 ta va 130x120x1ta 123_12 zakazdan, ombor burchagida turibdi"
JSON: {
  "cmd": "batch_add",
  "items": [
    { "category": "LDSP", "material": "Dub karmen 16 mm", "width": 1300, "height": 120, "qty": 1, "order": "123_12", "location": "Ombor burchagida" },
    { "category": "LDSP", "material": "Dub karmen 16 mm", "width": 130, "height": 120, "qty": 1, "order": "123_12", "location": "Ombor burchagida" }
  ]
}

User: "oq mdf qidir 1.2 metrli"
JSON: { "cmd": "search", "query": "oq mdf 1200" }

User: "id 13 da nima bor?"
JSON: { "cmd": "search", "query": "#13" }

User: "Barcha xdflar bormi?"
JSON: { "cmd": "search", "query": "XDF" }
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
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"cmd": "error", "msg": "Tushunarsiz buyruq"}
        
    except Exception as e:
        print(f"❌ AI Tahlil xatosi: {e}")
        return {"cmd": "error", "msg": str(e)}
