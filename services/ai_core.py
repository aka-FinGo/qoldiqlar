import json
import re # JSONni tozalash uchun kerak
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """
Sen mebel sexi omborini boshqaruvchi aqlli botsan.
Foydalanuvchi matnini tahlil qilib, quyidagi JSON formatda javob qaytar.

BUYRUQLAR (cmd):
1. "search" - Qidiruv. Params: { "query": "oq dsp" }
2. "batch_add" - Qo'shish.
   Params: "items": [ { "category": "...", "material": "...", "width": int, "height": int, "qty": int, "order": "...", "location": "..." } ]

MUHIM QOIDALAR:
1. O'lchamlar odatda "Uzunlik x Eni" formatida bo'ladi (Masalan: 500x300).
2. Agar "500x300x2" yoki "500x300x2ta" deyilsa, oxirgi raqam (2) bu SONI (qty) deb qabul qilinadi.
3. Material nomini aniq ajrat (MDF, LDSP, XDF, Akril). Rangi bo'lsa qo'shib yoz (Oq XDF).
4. Agar "zakazdan" so'zi bo'lsa, uni 'order' ga yoz.
5. JSON javobdan boshqa HECH NARSA yozma.

MISOLLAR:
User: "Oq dsp 1200x300 dan 5 ta, 500x200 dan 1 ta 123-zakaz"
JSON:
{
  "cmd": "batch_add",
  "items": [
    {"material": "Oq dsp", "width": 1200, "height": 300, "qty": 5, "order": "123"},
    {"material": "Oq dsp", "width": 500, "height": 200, "qty": 1, "order": "123"}
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
        
        # Ba'zan AI tushuntirish berib yuboradi, biz faqat JSONni qirqib olamiz
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = response_text[start:end]
            return json.loads(json_str)
        else:
            return {"cmd": "error", "msg": "JSON topilmadi"}
        
    except Exception as e:
        print(f"AI Xatosi: {e}")
        return {"cmd": "error", "msg": str(e)}
