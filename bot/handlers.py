from aiogram import Router, types, F
from aiogram.filters import Command
from services.ai_core import analyze_message
from services.gsheets import sync_new_user, sync_new_remnant
import database.queries as db

router = Router()

# Admin Username (Userlar bog'lanishi uchun)
ADMIN_USERNAME = "@iRealBy_3d" # <-- SHU YERGA O'ZINGIZNIKINI YOZING

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    
    # 1. Bazadan tekshiramiz (yoki yangi qo'shamiz)
    db_user = db.get_or_create_user(user.id, user.full_name, user.username)
    
    # 2. Agar yangi bo'lsa -> Google Sheetga ham yozib qo'yamiz
    if db_user and db_user.get('is_new'):
        sync_new_user(user.id, user.full_name)
        await message.answer(
            f"👋 Salom, {user.full_name}!\n\n"
            "🚫 **Sizda hozircha botdan foydalanishga ruxsat yo'q.**\n"
            "Iltimos, administrator bilan bog'laning va ruxsat so'rang.\n\n"
            f"👨‍💻 Admin: {ADMIN_USERNAME}"
        )
        return

    # 3. Agar eski user bo'lsa lekin bloklangan bo'lsa
    if db_user and db_user.get('can_search') == 0:
        await message.answer(f"🔒 **Sizning profilingiz faolsizlantirilgan.**\nAdminga yozing: {ADMIN_USERNAME}")
        return

    # 4. Ruxsati borlarga
    await message.answer(
        "👋 **Xush kelibsiz!**\n\n"
        "Bot tayyor. Menga 'Oq dsp bormi?' deb yozishingiz mumkin."
    )

@router.message(F.text)
async def handle_text(message: types.Message):
    user = message.from_user
    
    # --- XAVFSIZLIK TEKSHIRUVI ---
    db_user = db.get_or_create_user(user.id, user.full_name, user.username)
    
    # Agar user bazada yo'q bo'lsa yoki 'can_search' ruxsati 0 bo'lsa
    if not db_user or db_user.get('can_search') == 0:
        await message.answer(f"⛔️ **Ruxsat yo'q!**\nAdmin bilan bog'laning: {ADMIN_USERNAME}")
        return
    # -----------------------------

    status_msg = await message.answer("🤔 _O'ylayapman..._", parse_mode="Markdown")
    ai_result = await analyze_message(message.text)
    
    if not ai_result or ai_result.get('cmd') == 'error':
        await status_msg.edit_text("❌ Tushunmadim.")
        return

    cmd = ai_result.get('cmd')
    
    # --- QIDIRUV ---
    if cmd == 'search':
        # Qidiruv ruxsati bormi? (Garchi tepada tekshirgan bo'lsak ham)
        if db_user.get('can_search') == 0:
            await status_msg.edit_text("🔒 Sizga qidirish mumkin emas.")
            return
            
        query_text = ai_result.get('query', message.text)
        results = db.search_remnants(query_text)
        
        if not results:
            await status_msg.edit_text("🤷‍♂️ Hech narsa topilmadi.")
        else:
            text = f"✅ **Natijalar ({len(results)} ta):**\n\n"
            for item in results:
                text += f"🔹 **{item['material']}** | {item['width']}x{item['height']} | {item['qty']} dona\n"
                text += f"   📍 {item['location']} (#{item['id']})\n\n"
            await status_msg.edit_text(text, parse_mode="Markdown")

    # --- QO'SHISH ---
    elif cmd == 'batch_add':
        # Qo'shish ruxsati bormi? (Buni alohida tekshiramiz)
        if db_user.get('can_add') == 0:
            await status_msg.edit_text("🚫 **Sizda qoldiq qo'shish huquqi yo'q.** faqat qidira olasiz.")
            return

        items = ai_result.get('items', [])
        report = "💾 **Saqlandi:**\n"
        
        for item in items:
            new_id = db.add_remnant(
                category=item.get('category'),
                material=item.get('material'),
                width=item.get('width'),
                height=item.get('height'),
                qty=item.get('qty', 1),
                order=item.get('order'),
                location=item.get('location'),
                user_id=message.from_user.id,
                user_name=message.from_user.full_name
            )
            if new_id:
                report += f"✅ {item.get('material')} (#{new_id})\n"
                # Sheetga yozish
                sync_new_remnant({
                    'id': new_id,
                    'category': item.get('category'),
                    'material': item.get('material'),
                    'width': item.get('width'),
                    'height': item.get('height'),
                    'qty': item.get('qty', 1),
                    'origin_order': item.get('order'),
                    'location': item.get('location'),
                    'user_id': message.from_user.id,
                    'user_name': message.from_user.full_name
                })
        
        await status_msg.edit_text(report, parse_mode="Markdown")
