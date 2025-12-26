import json
import re
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

# Modellarni kuchiga qarab tartiblaymiz
# 1-o'rinda eng kuchlisi (Llama 3.3 70B), 2-o'rinda tez va arzonrog'i (Mixtral yoki Llama 3 8B)
AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",   # Asosiy kuchli model (juda aqlli)
    "mixtral-8x7b-32768",        # Zaxira (juda tez)
    "gemma2-9b-it"               # Favqulodda holat uchun
]

INSTRUCTIONS = """
Sen mebel materiallari omborini boshqaruvchi AI logistsan.
Vazifang: User matnini tahlil qilib, FAQAT JSON formatda natija qaytarish.
Hech qanday qo'shimcha so'z yozma!

QOIDALAR:
1. Kategoriya (LDSP, MDF, XDF) va Material (Oq, Kashemir, Dub) ajrat.
2. O'lcham (1500x200) va Soni (2 ta) ni aniqla.
3. Buyurtma (150_12, zakaz) va Lokatsiya (Zamin, Ombor) ni ajrat.

FORMAT:
User: "LDSP Kashemir 1500x150x1 zakaz 150_12"
JSON: {"cmd": "batch_add", "items": [{"category": "LDSP", "material": "Kashemir", "width": 1500, "height": 150, "qty": 1, "order": "150_12", "location": ""}]}

User: "oq mdf bormi"
JSON: {"cmd": "search", "keywords": ["oq", "mdf"]}
"""

def extract_json(text):
    """Matn ichidan toza JSON ni ajratib oladi"""
    try:
        # Markdown ```json ... ``` qidirish
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match: return json.loads(json_match.group(1))
        
        # Oddiy {...} qidirish
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match: return json.loads(json_match.group(0))
        
        return None
    except: return None

async def analyze_message(text):
    # Ro'yxatdagi har bir modelni navbat bilan sinab ko'ramiz
    for model_name in AVAILABLE_MODELS:
        try:
            # print(f"🤖 Model ishlamoqda: {model_name}...") # Log uchun (xohlasangiz yoqing)
            
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": INSTRUCTIONS},
                    {"role": "user", "content": text}
                ],
                model=model_name,
                temperature=0.1, # Aniq javob uchun past harorat
            )
            
            response_text = chat_completion.choices[0].message.content.strip()
            
            # JSONni tozalab ko'ramiz
            result = extract_json(response_text)
            
            if result:
                # Agar muvaffaqiyatli bo'lsa, darhol natijani qaytarib, tsiklni to'xtatamiz
                return result
            
            # Agar JSON bo'lmasa, keyingi modelga o'tish uchun "continue" qilamiz
            # print(f"⚠️ {model_name} JSON qaytarmadi, keyingisiga o'tamiz...")
            continue

        except Exception as e:
            # Agar API xatosi (Rate Limit va h.k.) bo'lsa, log yozib keyingisiga o'tamiz
            print(f"❌ Xatolik ({model_name}): {e}")
            continue

    # Agar hamma modellar xato qilsa:
    return {"cmd": "error"}
