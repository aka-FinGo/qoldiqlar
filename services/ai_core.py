import json
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """
Sen mebel sexi omborini boshqaruvchi aqlli botsan.
Foydalanuvchi matnini tahlil qilib, FAQAT JSON qaytar.

BUYRUQLAR:
1. "search" - Qidiruv.
2. "batch_add" - Qo'shish.

MUHIM QOIDALAR (Qo'shish uchun):
1. O'lchamlar formati: "Uzunlik x Eni" (500x300).
2. SONI (QTY):
   - Agar "500x300x2" yoki "500x300x2ta" desa -> qty=2, qalinlik emas!
   - Agar "2 dona", "2 sht" desa -> qty=2.
   - Default = 1.
3. KATEGORIYA (Category):
   - Agar user aytmasa, material nomidan ajratib ol.
   - "Oq XDF" -> Category="XDF", Material="Oq"
   - "Mokko" -> Category="LDSP" (Default)
   - "MDF", "LMDF", "Akril" so'zlari bu Kategoriya.
4. ORDER (Zakaz): "123-zakaz", "123_12", "Ali aka uchun" kabi gaplarni 'order' ga yoz.
5. LOCATION (Joy): "Sexda", "Zamin barakada", "Skladda" -> 'location' ga yoz.

MISOLLAR:
User: "1500x150x1TA xdf oq, Zamin barakada, 123_12 zakazdan"
JSON:
{
  "cmd": "batch_add",
  "items": [
    {
      "category": "XDF",
      "material": "Oq",
      "width": 1500,
      "height": 150,
      "qty": 1,
      "location": "Zamin baraka",
      "order": "123_12"
    }
  ]
}
"""

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
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1:
            return json.loads(response_text[start:end])
        return {"cmd": "error"}
        
    except Exception as e:
        print(f"AI Xatosi: {e}")
        return {"cmd": "error", "msg": str(e)}
