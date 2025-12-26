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

BUYURTMA RAQAMI (order) QOIDASI:
- Agar matnda "150_12", "123-55", "№50" yoki "zakazdan" so'zidan oldin/keyin kelgan raqamlar bo'lsa, ularni 'order' maydoniga yoz.
- BUYURTMA (order): "123_12", "№50", "Ali aka zakazi" kabi identifikatorlarni ajrat.
- Misol: "150_12 zakazdan qoldi" -> order: "150_12"

LOKATSIYA (location) QOIDASI:
- Material, o'lcham va orderdan boshqa barcha so'zlarni (masalan: "Zamin baraka", "Ombor", "brak") 'location' maydoniga jamla.
- LOKATSIYA VA IZOH (location): O'lcham, material va zakaz raqamidan tashqari barcha so'zlarni (joyi, holati, sababi, brak ekanligi) bitta matn qilib 'location' maydoniga jamla. 

QOIDALAR:
- O'LCHAM: Millimetrda hisobla (1.2 metr = 1200). "Uzunlik x Eni" formatida ajrat.
- MATERIAL: Kategoriya (XDF, LDSP, MDF, Akril, Dsp) va rangini (Oq, Dub karmen, Qora, antratsit, kashemir, beliy brilliant, snonoviy kost, agt 3019, agt 3020) aniq ajrat.
- SONI: "x2", "3ta", "5 dona" kabilarni raqamga aylantir. Default=1.
  * "Sex" so'zini ishlatma, o'rniga "Ombor" yoki user aytgan joyni yoz.
  * Masalan: "Zamin barakada, brak chiqdi, chekkasi urilgan" -> hammasi 'location'ga.

  MANTIQIY QOIDALAR:
1. "Detal kessa bo'ladimi?" - Agar foydalanuvchi "200 mm li detal kessa bo'ladigan" desa, u holda width >= 200 va height >= 200 bo'lgan materiallarni qidirish kerak.
2. "Yaqin oraliqda" - Agar "1200 ga yaqin" desa, o'lchamni 1200 deb ol va JSONda 'fuzzy': true belgisini qo'sh.
3. "Qora nimadir" - Material turini 'qora' deb ol.

JSON FORMATI:
{
  "cmd": "search",
  "query": "oq ldsp", 
  "requirements": {
    "min_width": 1000, 
    "min_height": 200,
    "is_flexible": true  # Yaqin oraliq yoki kesish mantiqi uchun
  }
}
"""

# --- 2. KENGAYTIRILGAN MISOLLAR (EXAMPLES) ---
EXAMPLES = """
MISOLLAR:
User: "LDSP OQ 1570x150x1TA QOLDIQ 150_12 ZAKAZDAN QOLDI"
JSON: {
  "cmd": "batch_add",
  "items": [{
    "category": "LDSP", 
    "material": "Oq", 
    "width": 1570, 
    "height": 150, 
    "qty": 1, 
    "order": "150_12", 
    "location": "Zakazdan qoldi"
  }]
}

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
