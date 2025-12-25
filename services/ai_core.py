import json
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

# Bu AI uchun "Konstitutsiya". Uni qanchalik aniq yozsak, shunchalik zo'r ishlaydi.
SYSTEM_PROMPT = """
Sen mebel sexi omborini boshqaruvchi aqlli botsan.
Foydalanuvchi matnini tahlil qilib, quyidagi JSON formatda javob qaytar.
Javobingda faqat JSON bo'lsin, ortiqcha gap yozma.

BUYRUQLAR (cmd):
1. "search" - Qidiruv. Params: { "query": "oq dsp" }
2. "batch_add" - Qo'shish.
   Params: "items": [ { "category": "...", "material": "...", "width": int, "height": int, "qty": int, "order": "...", "location": "..." } ]

QOIDALAR:
1. Agar user bir nechta material aytsa (masalan: "oq xdf va mdf"), ularni alohida item qilib "items" ichiga joyla.
2. Agar gapda umumiy zakaz raqami (masalan: "123_10") yoki joy (masalan: "Sexda") aytilsa, buni barcha itemlarga qo'shib yoz (Meros olish).
3. O'lchamlarni mm ga o'tkaz (agar sm deyilsa).
4. Material nomini aniqlashga harakat qil (LDSP, MDF, XDF).
"""

async def analyze_message(text):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            model="llama-3.3-70b-versatile", # Eng kuchli model
            temperature=0.1, # Aniq javob uchun
        )
        
        response_text = chat_completion.choices[0].message.content
        
        # JSONni tozalab olish (ba'zan AI ```json deb yozib yuboradi)
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        json_str = response_text[start:end]
        
        return json.loads(json_str)
        
    except Exception as e:
        print(f"AI Xatosi: {e}")
        return {"cmd": "error", "msg": str(e)}
