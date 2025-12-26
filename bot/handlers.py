import database.queries as db
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ai_core import analyze_message
from services.gsheets import sync_new_user, sync_new_remnant, get_all_users_from_sheet, update_sheet_status, update_sheet_qty
from config import ADMIN_ID, ADMIN_USERNAME

router = Router()

# FSM Holatlari
class AddState(StatesGroup):
    waiting_confirm = State()

# --- YORDAMCHI FUNKSIYALAR ---

def get_search_keyboard(query, offset, total_results):
    builder = InlineKeyboardBuilder()
    # Har bir natija uchun "Batafsil" tugmasi o'rniga, natijalar ostida navigatsiya
    if offset > 0:
        builder.button(text="⬅️ Orqaga", callback_data=f"search:{query}:{offset-5}")
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
    try:
        # Callback datadan ma'lumotlarni olamiz: search:query:offset
        parts = callback.data.split(":")
        if len(parts) < 3:
            return
            
        query = parts[1]
        offset = int(parts[2])
        
        # Bazadan yangi offset bo'yicha ma'lumotlarni olamiz
        results = db.search_remnants(query)
        
        if not results:
            await callback.answer("Natijalar topilmadi.")
            return

        # Matn va klaviaturani yangilaymiz
        text = format_search_results(results[offset:offset+5], len(results), offset)
        kb = get_search_keyboard(query, offset, len(results))
        
        # Xabarni tahrirlaymiz (Markdown o'rniga HTML ishlatgan bo'lsangiz parse_mode="HTML" qiling)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        
    except Exception as e:
        print(f"❌ Pagination error: {e}")
        await callback.answer("Xatolik yuz berdi")
    
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

@router.message(F.text.startswith("/view_"))
async def cmd_view_detail(message: types.Message):
    try:
        r_id = int(message.text.split("_")[1])
        await show_item_details(message, r_id)
    except:
        await message.answer("❌ Noto'g'ri ID")

@router.message(Command("sync"))
async def cmd_sync(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID): return
    
    status_msg = await message.answer("🔄 **Sinxronlash ketmoqda...**")
    sheet_users = get_all_users_from_sheet()
    
    count = 0
    for row in sheet_users:
        try:
            u_id, p_val = row[0], str(row[2]).lower().strip()
            status = 1 if p_val in ['1', 'true', 'ha', 'bor'] else 0
            db.update_user_permission(u_id, status)
            count += 1
        except: continue
    await status_msg.edit_text(f"✅ Bajarildi! {count} ta user ruxsati yangilandi.")

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
        query = ai_result.get('query')
        results = db.search_remnants(query)
        if not results:
            await message.answer(f"🤷‍♂️ '{query}' bo'yicha hech narsa topilmadi.")
            return
        
        text = format_search_results(results[:5], len(results), 0)
        kb = get_search_keyboard(query, 0, len(results))
        
        # MUHIM: parse_mode="HTML" bo'lishi shart!
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

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
