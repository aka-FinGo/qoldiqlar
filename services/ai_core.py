import json
import re
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

# --- 1. QAT'IY PROMPT ---
INSTRUCTIONS = """
Sen mebel ishlab chiqarish bo'yicha 30 yillik tajribaga ega AI logistsan.
Vazifang: User matnini tahlil qilib, FAQAT JSON formatda natija qaytarish.

KATEGORIYALARNI TANIB OLISH:
- LDSP, MDF, XDF, Akril, LMDF, DVP -> Bular 'category'.
- Kashemir, Oq, Qora, Antrasit, Dub -> Bular 'material'.

QOIDALAR:
1. Hech qanday izoh, kirish so'zi yoki yakunlovchi gap yozma.
2. Natija faqat '{' belgisi bilan boshlanib '}' bilan tugashi shart.
3. Agar o'lcham (1500x150) berilgan bo'lsa -> batch_add.
4. Agar faqat nom qidirilsa -> search.

MISOLLAR:
User: "LDSP Kashemir, 1500x150x1ta QOLDIQ qoldi, 150_12 zakazdan"
JSON: {
  "cmd": "batch_add",
  "items": [{
    "category": "LDSP",
    "material": "Kashemir",
    "width": 1500,
    "height": 150,
    "qty": 1,
    "order": "150_12",
    "location": "Ombor"
  }]
}

User: "oq mdf bormi"
JSON: {"cmd": "search", "keywords": ["oq", "mdf"]}
"""

def extract_json(text):
    """
    AI javobidan toza JSON ni ajratib oluvchi funksiya.
    Bu 'Extra data' xatosini 100% yo'q qiladi.
    """
    try:
        # 1-urinish: Markdown kod bloki ichini qidirish (```json ... ```)
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # 2-urinish: Oddiy {} qavslar ichini qidirish
        # Bu eng birinchi ochilgan { va eng oxirgi yopilgan } ni topadi
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
            
        return None
    except Exception as e:
        print(f"JSON Parsing Error: {e} | Text: {text}")
        return None

async def analyze_message(text):
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": INSTRUCTIONS},
                {"role": "user", "content": text}
            ],
            # 'groq/compound' yoki 'llama3-70b-8192' ishlatsangiz bo'ladi
            model="llama3-70b-8192", 
            temperature=0.1, # Past harorat = Aniqroq javob
        )
        
        response_text = chat_completion.choices[0].message.content.strip()
        
        # Yangi tozalovchi funksiya orqali o'tkazamiz
        result = extract_json(response_text)
        
        if result:
            return result
        else:
            print(f"⚠️ AI noto'g'ri format qaytardi: {response_text}")
            return {"cmd": "error"}
            
    except Exception as e:
        print(f"❌ AI Tahlil xatosi: {e}")
        return {"cmd": "error"}
