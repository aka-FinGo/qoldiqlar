from aiogram import Router, types, F
from aiogram.filters import Command
from services.ai_core import analyze_message
import database.queries as db

router = Router()

# 1. /start buyrug'i
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 **Salom! Men Mebel Qoldiqlari Botiman.**\n\n"
        "Menga shunchaki gapiring, men tushunaman:\n"
        "🔍 *Qidirish:* 'Oq dsp bormi?'\n"
        "➕ *Qo'shish:* 'Mokko 1200x300 dan 2 ta, 123-zakazdan qoldi'\n\n"
        "Boshlash uchun yozing! 👇",
        parse_mode="Markdown"
    )

# 2. Asosiy Matnli Xabarlar (AI bilan ishlash)
@router.message(F.text)
async def handle_text(message: types.Message):
    user_text = message.text
    status_msg = await message.answer("🤔 _O'ylayapman..._", parse_mode="Markdown")

    # 1-QADAM: Matnni AI ga beramiz
    ai_result = await analyze_message(user_text)
    
    # Agar AI tushunmasa yoki xato bo'lsa
    if not ai_result or ai_result.get('cmd') == 'error':
        await status_msg.edit_text("❌ Uzr, tushunmadim yoki tizimda xatolik.")
        return

    cmd = ai_result.get('cmd')
    
    # --- SENARIY A: QIDIRUV (SEARCH) ---
    if cmd == 'search':
        # AI bizga qidiruv so'zini beradi (masalan: "oq dsp")
        query_text = ai_result.get('query', user_text) # Agar query bo'lmasa, user so'zini olamiz
        
        results = db.search_remnants(query_text)
        
        if not results:
            await status_msg.edit_text(f"🔍 '{query_text}' bo'yicha hech narsa topilmadi.")
        else:
            # Javobni chiroyli qilish
            text = f"✅ **Topilgan qoldiqlar ({len(results)} ta):**\n\n"
            for item in results:
                # Bazadan kelgan ma'lumotlarni o'qiymiz
                # item['origin_order'] -> ba'zan None bo'lishi mumkin, shuning uchun 'get' ishlatamiz agar dict bo'lsa
                # Psycopg2 RealDictCursor ishlatganimiz uchun item bu Dictionary
                
                info = f"🔹 **{item['material']}** | {item['width']}x{item['height']} mm\n"
                info += f"   📍 Joy: {item['location'] or 'Noma`lum'}\n"
                info += f"   📦 Soni: {item['qty']} dona | ID: #{item['id']}\n\n"
                text += info
            
            await status_msg.edit_text(text, parse_mode="Markdown")

    # --- SENARIY B: QO'SHISH (BATCH ADD) ---
    elif cmd == 'batch_add':
        items = ai_result.get('items', [])
        added_count = 0
        report = "💾 **Qoldiqlar saqlandi:**\n\n"
        
        for item in items:
            # Bazaga yozamiz
            new_id = db.add_remnant(
                category=item.get('category', 'Boshqa'),
                material=item.get('material', 'Noma`lum'),
                width=item.get('width', 0),
                height=item.get('height', 0),
                qty=item.get('qty', 1),
                order=item.get('order', 'Noma`lum'),
                location=item.get('location', 'Sex'),
                user_id=message.from_user.id,
                user_name=message.from_user.full_name
            )
            
            if new_id:
                added_count += 1
                report += f"✅ **{item.get('material')}** {item.get('width')}x{item.get('height')} (#{new_id})\n"
            else:
                report += f"❌ **{item.get('material')}** (Xatolik bo'ldi)\n"
        
        await status_msg.edit_text(report, parse_mode="Markdown")
        
    # --- SENARIY C: TUSHUNARSIZ BUYRUQ ---
    else:
        await status_msg.edit_text("🤷‍♂️ AI buyruqni tushundi, lekin men bajara olmadim.")
