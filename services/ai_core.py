import json
import re
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

# --- 1. KOMPLEKS PROMPT ---
INSTRUCTIONS = """
Sen mebel materiallari omborini boshqaruvchi professional AI Robotsan. 
Foydalanuvchi xabarlarini tahlil qilib, FAQAT JSON qaytar.

BUYRUQLAR:
1. "search": Qidiruv. "oq mdf", "150x200 detail kessa bo'ladimi", "id 13" kabi so'rovlarda.
2. "batch_add": Yangi qoldiq qo'shish. O'lcham va material aytilganda.

MA'LUMOTLARNI AJRATISH QOIDALARI:
- O'LCHAM (width, height): Millimetrda. 1.2 metr = 1200. "1500 ga 200" bo'lsa, width=1500, height=200.
- BUYURTMA (order): "150_12", "123-55", "№50" yoki "zakazdan qoldi" so'zidan oldingi/keyingi kodlar.
- LOKATSIYA (location): Material va o'lchamdan tashqari barcha izohlar (masalan: "Zamin baraka", "brak", "chekkasi urilgan").
- MATERIAL: Kategoriya (LDSP, MDF, XDF, Akril) va uning rangi/turi.

MANTIQIY QIDIRUV (Requirements):
- Agar "200 mm li detal kessa bo'ladimi" desa: min_width=200, min_height=200.
- Agar "1200 ga yaqin" desa: is_flexible=True.

JSON FORMATI:
{
  "cmd": "search" | "batch_add",
  "query": "matn",
  "requirements": {"min_width": int, "min_height": int, "is_flexible": bool},
  "items": [{"category": str, "material": str, "width": int, "height": int, "qty": int, "order": str, "location": str}]
}
"""

EXAMPLES = """
User: "LDSP OQ 1570x150x1TA 150_12 zakazdan qoldi, Zamin barakada"
JSON: {"cmd": "batch_add", "items": [{"category": "LDSP", "material": "Oq", "width": 1570, "height": 150, "qty": 1, "order": "150_12", "location": "Zamin baraka, zakazdan qoldi"}]}

User: "oq mdf 1200 metrli qidir"
JSON: {"cmd": "search", "query": "oq mdf 1200"}

User: "300x300 detal kessa bo'ladigan qora nimadir bormi?"
JSON: {"cmd": "search", "query": "qora", "requirements": {"min_width": 300, "min_height": 300, "is_flexible": true}}
"""

async def analyze_message(text):
    try:
        # Model groq/compound ga o'zgartirildi
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": INSTRUCTIONS + EXAMPLES},
                {"role": "user", "content": text}
            ],
            model="groq/compound",
            temperature=0.1,
        )
        
        response_text = chat_completion.choices[0].message.content
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"cmd": "error"}
    except Exception as e:
        print(f"❌ AI Tahlil xatosi: {e}")
        return {"cmd": "error"}
