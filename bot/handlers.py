import database.queries as db
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ai_core import analyze_message
from services.gsheets import sync_new_user, sync_new_remnant, get_all_users_from_sheet, update_sheet_status, update_sheet_qty, get_all_remnants_from_sheet
from config import ADMIN_ID, ADMIN_USERNAME

router = Router()

# FSM Holatlari
class AddState(StatesGroup):
    waiting_confirm = State()

# --- YORDAMCHI FUNKSIYALAR ---

def get_search_keyboard(query, offset, total_results):
    builder = InlineKeyboardBuilder()
    
    # Orqaga tugmasi (faqat offset 0 dan katta bo'lsa)
    if offset > 0:
        builder.button(text="⬅️ Orqaga", callback_data=f"search:{query}:{max(0, offset-5)}")
    
    # Oldinga tugmasi (agar yana natijalar bo'lsa)
    if offset + 5 < total_results:
        builder.button(text="Oldinga ➡️", callback_data=f"search:{query}:{offset+5}")
    
    builder.adjust(2)
    return builder.as_markup()

def format_search_results(items, total, offset):
    # Markdown o'rniga HTML teglari: <b> (bold)
    text = f"🔍 <b>Natijalar:</b> (Jami: {total})\n\n"
    for i, item in enumerate(items, 1):
        item_id = item['id']
        # Xatolikni oldini olish uchun ma'lumotlarni tekstga aylantiramiz
        cat = str(item.get('category', ''))
        mat = str(item.get('material', ''))
        loc = str(item.get('location', ''))
        
        text += (f"{offset + i}. <b>{cat} {mat}</b>\n"
                 f"📏 {item['width']}x{item['height']} | 📦 {item['qty']} ta\n"
                 f"📍 {loc} | /view_{item_id}\n" # Tagchiziq bilan /view_id
                 f"----------------------------\n")
    return text

# Xabarni yuborishda:
# await message.answer(text, reply_markup=kb, parse_mode="HTML")



@router.callback_query(F.data.startswith("search:"))
async def process_search_pages(callback: types.CallbackQuery):
    _, query, offset = callback.data.split(":")
    offset = int(offset)
    
    # Agar query "ALL_LIST" bo'lsa, hamma aktiv qoldiqlarni olamiz
    if query == "ALL_LIST":
        results = db.get_all_active_remnants()
    else:
        results = db.search_remnants(query)
    
    if not results:
        return await callback.answer("Boshqa natija yo'q")

    text = format_search_results(results[offset:offset+5], len(results), offset)
    kb = get_search_keyboard(query, offset, len(results))
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()
    

@router.callback_query(F.data.startswith("use:"))
async def process_use(callback: types.CallbackQuery, bot: Bot):
    try:
        # 1. IDni ajratib olamiz
        r_id = int(callback.data.split(":")[1])
        print(f"DEBUG: Ishlatish so'raldi ID={r_id}, User={callback.from_user.id}")
        
        success = db.use_remnant(r_id, callback.from_user.id)
        
        # 2. Bazada statusni 0 qilamiz
        # queries.py dagi use_remnant(r_id, user_id) chaqiriladi
        
        if success:
            # 3. Google Sheetda ham statusni 0 qilamiz
            try:
                update_sheet_status(r_id, 0)
                await callback.message.edit_text(f"📉 <b>ID #{r_id}</b> ishlatilgan deb belgilandi.", parse_mode="HTML")
            except Exception as e:
                print(f"⚠️ Sheet update error (lekin baza yangilandi): {e}")

            # 4. Foydalanuvchiga javob
            await callback.message.edit_text(f"📉 <b>ID #{r_id}</b> ishlatilgan deb belgilandi va ro'yxatdan olindi.", parse_mode="HTML")
            
            # 5. Adminga bildirishnoma
            if str(callback.from_user.id) != str(ADMIN_ID):
                await bot.send_message(
                    ADMIN_ID, 
                    f"📉 <b>Qoldiq ishlatildi!</b>\n"
                    f"🆔 ID: #{r_id}\n"
                    f"👤 Kim: {callback.from_user.full_name}",
                    parse_mode="HTML"
                )
        else:
            await callback.answer("❌ Bu qoldiq allaqachon ishlatilgan yoki topilmadi.", show_alert=True)

    except Exception as e:
        # Render logda aniq xatoni ko'rish uchun:
        print(f"❌ CRITICAL ERROR in process_use: {e}") 
        await callback.answer("❌ Tizim xatosi: Loglarni tekshiring", show_alert=True)

@router.callback_query(F.data == "confirm_add", AddState.waiting_confirm)
async def confirm_add(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    item = data['new_item']
    
    new_total_qty = db.update_qty(data['existing_id'], item['qty'])
    if new_total_qty:
        update_sheet_qty(data['existing_id'], new_total_qty)
        await callback.message.edit_text(f"✅ Soni yangilandi! Jami: **{new_total_qty}** ta.")
        
        if str(callback.from_user.id) != str(ADMIN_ID):
            await bot.send_message(ADMIN_ID, f"🔄 **Dublikat yangilandi!**\nID: #{data['existing_id']}\nJami: {new_total_qty} ta\nUser: {callback.from_user.full_name}")
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_add", AddState.waiting_confirm)
async def cancel_add(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Bekor qilindi.")
    await state.clear()
    await callback.answer()
    # --- COMMAND HANDLERS ---

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    db_user = db.get_or_create_user(user.id, user.full_name, user.username)
    
    if db_user and db_user.get('is_new'):
        sync_new_user(user.id, user.full_name)
        await message.answer(f"👋 Salom! Siz ro'yxatga olindingiz.\nBotdan foydalanish uchun admin ruxsati kerak: {ADMIN_USERNAME}")
        return

    await message.answer("👋 Xush kelibsiz! Material qidirish yoki qo'shish uchun xabar yozing.")

# --- YANGI BUYRUQLAR: /ishlatilganlar, /men_ishlatganlarim, /list ---

@router.message(Command("ishlatilganlar"))
async def cmd_all_used(message: types.Message):
    items = db.get_used_remnants() # Hammaniki
    if not items:
        return await message.answer("📭 Ishlatilgan qoldiqlar hali yo'q.")
    
    text = "📂 <b>Barcha ishlatilgan qoldiqlar:</b>\n\n"
    text += format_search_results(items[:10], len(items), 0)
    await message.answer(text, parse_mode="HTML")

@router.message(Command("men_ishlatganlarim"))
async def cmd_my_used(message: types.Message):
    items = db.get_used_remnants(user_id=message.from_user.id)
    if not items:
        return await message.answer("📭 Siz hali qoldiq ishlatmagansiz.")
    
    text = "👤 <b>Siz ishlatgan qoldiqlar:</b>\n\n"
    text += format_search_results(items[:10], len(items), 0)
    await message.answer(text, parse_mode="HTML")

# --- QAYTARIB QO'YISH CALLBACK ---
@router.callback_query(F.data.startswith("restore:"))
async def process_restore(callback: types.CallbackQuery):
    try:
        r_id = int(callback.data.split(":")[1])
        # Bazada statusni 1 qilamiz va used_by ni tozalaymiz
        success = db.restore_remnant(r_id)
        
        if success:
            # GSheets'da statusni 1 qilamiz
            from services.gsheets import update_sheet_status
            update_sheet_status(r_id, 1)
            
            await callback.message.edit_text(f"🔄 ID #{r_id} omborga qaytarildi va mavjud deb belgilandi.")
        else:
            await callback.answer("❌ Xato: Qoldiqni qaytarib bo'lmadi.", show_alert=True)
    except Exception as e:
        print(f"❌ Restore error: {e}")
        await callback.answer("❌ Tizim xatosi")
    await callback.answer()

# --- /list BUYRUG'I (5 tadan chiqarish) ---
@router.message(Command("list"))
async def cmd_list_all(message: types.Message):
    items = db.get_all_active_remnants()
    if not items:
        return await message.answer("📭 Omborda qoldiq mavjud emas.")
    
    # Faqat birinchi 5 tasini ko'rsatamiz
    text = f"📋 <b>Mavjud qoldiqlar</b> (Jami: {len(items)} ta):\n\n"
    text += format_search_results(items[:5], len(items), 0)
    
    # Tugmalarni chiqarish (Pagination)
    kb = get_search_keyboard("ALL_LIST", 0, len(items))
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    

# --- QAYTARIB QO'YISH TUGMASI LOGIKASI ---

@router.message(F.text.startswith("/view_"))
async def cmd_view_detail(message: types.Message):
    try:
        r_id = int(message.text.split("_")[1])
        item = db.get_remnant_details(r_id)
        
        if not item:
            return await message.answer("❌ Ma'lumot topilmadi.")

        created_date = item['created_at'].strftime('%d.%m.%Y %H:%M')
        text = (f"📑 <b>Ma'lumot (ID: #{item['id']})</b>\n\n"
                f"🛠 <b>Material:</b> {item['category']} {item['material']}\n"
                f"📏 <b>O'lcham:</b> {item['width']}x{item['height']} mm\n"
                f"📦 <b>Soni:</b> {item['qty']} ta\n"
                f"👤 <b>Qo'shdi:</b> {item['created_by_name']}\n"
                f"📅 <b>Sana:</b> {created_date}\n")
        
        kb = InlineKeyboardBuilder()
        
        if item['status'] == 1:
            kb.button(text="✅ Ishlatish (Olish)", callback_data=f"use:{item['id']}")
        else:
            text += f"\n⚠️ <b>Holat:</b> Ishlatilgan"
            # FAQAT ISHLATGAN ODAM YOKI ADMIN QAYTARA OLADI
            if str(item['used_by']) == str(message.from_user.id) or str(message.from_user.id) == str(ADMIN_ID):
                kb.button(text="🔄 Qaytarib qo'yish", callback_data=f"restore:{item['id']}")
            else:
                text += f"\n👤 <b>Kim tomonidan:</b> Boshqa ishchi"

        await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception as e:
        print(f"View error: {e}")


@router.message(Command("sync"))
async def cmd_sync(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID): return
    
    status_msg = await message.answer("🔄 <b>Majburiy sinxronlash boshlandi...</b>", parse_mode="HTML")
    
    try:
        # 1. Userlarni yangilash
        users = get_all_users_from_sheet()
        for row in users:
            try:
                db.update_user_permission(row[0], 1 if str(row[2]).lower() in ['1', 'true', 'ha'] else 0)
            except: continue
        
        # 2. Qoldiqlarni Sheetdan bazaga qayta yozish
        remnants = get_all_remnants_from_sheet()
        for r in remnants:
            try:
                # r[0]-ID, r[3]-material, r[4]-width, r[5]-height, r[6]-qty, r[9]-order, r[10]-location, r[11]-status
                db.sync_remnant_from_sheet(
                    r[0], r[3], int(r[4]), int(r[5]), int(r[6]), 
                    r[9], # BUYURTMA RAQAMI
                    r[10], # LOKATSIYA
                    int(r[11]) # STATUS
                )
            except: continue
            
        await status_msg.edit_text("✅ <b>Baza va GSheets to'liq sinxronlandi!</b>", parse_mode="HTML")
    except Exception as e:
        await status_msg.edit_text(f"❌ Xato: {e}")

# --- CALLBACK HANDLERS ---



# --- ASOSIY FUNKSIYALAR ---

async def show_item_details(message: types.Message, r_id: int):
    item = db.get_remnant_details(r_id)
    if not item:
        await message.answer("❌ Topilmadi.")
        return

    # Ma'lumotlarni tayyorlash
    created_date = item['created_at'].strftime('%d.%m.%Y %H:%M')
    # HTML formatida maxsus belgilarni xavfsiz qilish uchun:
    order_val = str(item['origin_order']) if item['origin_order'] else "Yo'q"
    location_val = str(item['location']) if item['location'] else "Noma'lum"

    # HTML formatida xabar matni
    text = (f"📑 <b>To'liq ma'lumot (ID: #{item['id']})</b>\n\n"
            f"🛠 <b>Material:</b> {item['category']} {item['material']}\n"
            f"📏 <b>O'lcham:</b> {item['width']}x{item['height']} mm\n"
            f"📦 <b>Soni:</b> {item['qty']} ta\n"
            f"🔢 <b>Buyurtma:</b> {order_val}\n"
            f"📍 <b>Izoh/Joy:</b> {location_val}\n"
            f"👤 <b>Qo'shdi:</b> {item['created_by_name']}\n"
            f"📅 <b>Sana:</b> {created_date}")
    
    kb = InlineKeyboardBuilder()
    if item['status'] == 1:
        kb.button(text="✅ Ishlatish (Olish)", callback_data=f"use:{item['id']}")
    else:
        kb.button(text="🔄 Qaytarib qo'yish", callback_data=f"restore:{item['id']}")
    kb.adjust(1)
    
    # MUHIM: parse_mode="HTML" bo'lishi kerak
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext, bot: Bot):
    if message.text.startswith('/'): return

    db_user = db.get_or_create_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    if not db_user or db_user.get('can_search') == 0:
        await message.answer(f"⛔️ Ruxsat yo'q. Admin: {ADMIN_USERNAME}")
        return

    ai_result = await analyze_message(message.text)
    if not ai_result or ai_result.get('cmd') == 'error':
        await message.answer("❓ Tushunarsiz buyruq. Iltimos, aniqroq yozing.")
        return

    cmd = ai_result.get('cmd')


    
    if cmd == 'search':
        req = ai_result.get('requirements', {})
        results = db.smart_search(
            query = ai_result.get('query', ''),
            min_w = req.get('min_width', 0),
            min_h = req.get('min_height', 0),
            is_flexible = req.get('is_flexible', False)
        )
        
        if not results:
            await message.answer("😔 Afsuski, bu o'lchamdagi detal kessa bo'ladigan material topilmadi.")
            return

        text = f"🎯 <b>Sizning o'lchamingizga mos keladiganlar:</b>\n\n"
        text += format_search_results(results, len(results), 0)
        await message.answer(text, parse_mode="HTML")

    

    elif cmd == 'batch_add':
        if db_user.get('can_add') == 0:
            await message.answer("🚫 Sizda qo'shish huquqi yo'q.")
            return

        for item in ai_result.get('items', []):
            existing = db.check_duplicate(item['material'], item['width'], item['height'], item['location'])
            if existing:
                await state.set_state(AddState.waiting_confirm)
                await state.update_data(new_item=item, existing_id=existing['id'], current_qty=existing['qty'])
                kb = InlineKeyboardBuilder()
                kb.button(text="✅ Ha, qo'shilsin", callback_data="confirm_add")
                kb.button(text="❌ Bekor qilish", callback_data="cancel_add")
                await message.answer(f"⚠️ **Dublikat!**\n{item['material']} ({item['width']}x{item['height']}) omborda bor. Soni: {existing['qty']}. Yana {item['qty']} ta qo'shilsinmi?", reply_markup=kb.as_markup(), parse_mode="Markdown")
            else:
                new_id = db.add_remnant_final(item, message.from_user.id, message.from_user.full_name)
                if new_id:
                    sync_new_remnant({'id': new_id, **item, 'user_id': message.from_user.id, 'user_name': message.from_user.full_name})
                    await message.answer(f"✅ **Yangi qoldiq saqlandi!**\n🆔 ID: #{new_id}\n🛠 {item['category']} {item['material']}\n📏 {item['width']}x{item['height']} mm\n📍 {item['location']}", parse_mode="Markdown")
                    if str(message.from_user.id) != str(ADMIN_ID):
                        await bot.send_message(ADMIN_ID, f"🔔 **Yangi qoldiq!**\nUser: {message.from_user.full_name}\nMaterial: {item['material']} (#{new_id})")
