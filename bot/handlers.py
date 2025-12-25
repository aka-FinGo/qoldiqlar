from aiogram import Router, types, F
from aiogram.filters import Command
from services.ai_core import analyze_message
from services.gsheets import sync_new_user, sync_new_remnant, get_all_users_from_sheet
import database.queries as db

router = Router()

# Admin Username (Userlar bog'lanishi uchun)
ADMIN_USERNAME = "@SizningUsername" 

# --- 1. START BUYRUG'I (ENG TEPADA) ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    db_user = db.get_or_create_user(user.id, user.full_name, user.username)
    
    if db_user and db_user.get('is_new'):
        sync_new_user(user.id, user.full_name)
        await message.answer(f"👋 Salom! Sizda ruxsat yo'q. Admin bilan bog'laning: {ADMIN_USERNAME}")
        return

    if db_user and db_user.get('can_search') == 0:
        await message.answer("🔒 Profilingiz nofaol.")
        return

    await message.answer("👋 **Bot tayyor!**\n\nNima qidiramiz yoki qo'shamiz?")

# --- 2. SYNC BUYRUG'I (MATNDAN OLDIN TURISHI SHART!) ---
@router.message(Command("sync"))
async def cmd_sync(message: types.Message):
    status_msg = await message.answer("🔄 **Google Sheet bilan sinxronlash ketmoqda...**")
    sheet_users = get_all_users_from_sheet()
    
    if not sheet_users:
        await status_msg.edit_text("❌ Sheetdan ma'lumot o'qib bo'lmadi.")
        return

    count = 0
    for row in sheet_users:
        try:
            # Sheet tuzilishi: A=ID (0), C=Ruxsat (2)
            if len(row) < 3: continue 
            
            user_id = row[0]
            permission_val = str(row[2]).lower().strip()
            
            # Agar 1, true, ha bo'lsa -> Ruxsat beramiz
            if permission_val in ['1', 'true', 'ha', 'bor']:
                status = 1
            else:
                status = 0
                
            db.update_user_permission(user_id, status)
            count += 1
        except Exception as e:
            print(f"Sync xatosi: {e}")
            continue

    await status_msg.edit_text(f"✅ **Bajarildi!**\n{count} ta foydalanuvchi huquqlari yangilandi.")

# --- 3. MATNLI XABARLAR (ENG PASTDA) ---
@router.message(F.text)
async def handle_text(message: types.Message):
    user = message.from_user
    db_user = db.get_or_create_user(user.id, user.full_name, user.username)
    
    # Ruxsat tekshirish
    if not db_user or db_user.get('can_search') == 0:
        await message.answer("⛔️ Ruxsat yo'q.")
        return

    status_msg = await message.answer("🤔 _Tahlil qilyapman..._", parse_mode="Markdown")
    
    # AI tahlili
    ai_result = await analyze_message(message.text)
    
    if not ai_result or ai_result.get('cmd') == 'error':
        await status_msg.edit_text("❌ Tushunmadim, qayta yozing.")
        return

    cmd = ai_result.get('cmd')
    
    # --- SEARCH ---
    if cmd == 'search':
        query_text = ai_result.get('query', message.text)
        results = db.search_remnants(query_text)
        
        if not results:
            await status_msg.edit_text(f"🔍 '{query_text}' bo'yicha hech narsa topilmadi.")
        else:
            text = f"✅ **Topildi ({len(results)} ta):**\n\n"
            for item in results:
                text += f"🔹 **{item['material']}** | {item['width']}x{item['height']} | {item['qty']} dona\n"
                text += f"   📍 {item['location']} (#{item['id']})\n\n"
            await status_msg.edit_text(text, parse_mode="Markdown")

    # --- ADD ---
    elif cmd == 'batch_add':
        if db_user.get('can_add') == 0:
            await status_msg.edit_text("🚫 Sizda qo'shish huquqi yo'q.")
            return

        items = ai_result.get('items', [])
        if not items:
            await status_msg.edit_text("🤷‍♂️ O'lcham yoki materialni tushunmadim.\nMasalan: *Oq dsp 500x300 2 dona*")
            return

        report = "💾 **Saqlandi:**\n\n"
        for item in items:
            new_id = db.add_remnant(
                category=item.get('category', 'Boshqa'),
                material=item.get('material', 'Noma`lum'),
                width=item.get('width', 0),
                height=item.get('height', 0),
                qty=item.get('qty', 1),
                order=item.get('order', ''),
                location=item.get('location', 'Sex'),
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
                    'qty': item.get('qty'),
                    'origin_order': item.get('order'),
                    'location': item.get('location'),
                    'user_id': message.from_user.id,
                    'user_name': message.from_user.full_name
                })
        
        await status_msg.edit_text(report, parse_mode="Markdown")
