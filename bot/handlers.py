from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ai_core import analyze_message
from services.gsheets import sync_new_user, sync_new_remnant, get_all_users_from_sheet
import database.queries as db
from config import ADMIN_USERNAME

router = Router()

# FSM Holatlari
class AddState(StatesGroup):
    waiting_confirm = State()

# --- YORDAMCHI FUNKSIYALAR ---

def get_search_keyboard(query, offset, total_results):
    """Pagination tugmalarini yaratish"""
    builder = InlineKeyboardBuilder()
    if offset > 0:
        builder.button(text="⬅️ Orqaga", callback_data=f"search:{query}:{offset-5}")
    if offset + 5 < total_results:
        builder.button(text="Oldinga ➡️", callback_data=f"search:{query}:{offset+5}")
    builder.adjust(2)
    return builder.as_markup()

def format_search_results(items, total, offset):
    """Qidiruv natijalarini chiroyli formatlash"""
    text = f"🔍 **Natijalar:** (Jami: {total})\n\n"
    for i, item in enumerate(items, 1):
        text += f"{offset + i}. **{item['material']}**\n   📏 {item['width']}x{item['height']} | 📦 {item['qty']} ta\n   📍 {item['location']} | #{item['id']}\n\n"
    return text

# --- BUYRUQLAR (COMMANDS) ---

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    db_user = db.get_or_create_user(user.id, user.full_name, user.username)
    
    if db_user and db_user.get('is_new'):
        sync_new_user(user.id, user.full_name)
        await message.answer(f"👋 Salom! Siz ro'yxatga olindingiz, lekin ruxsatingiz yo'q.\nAdmin bilan bog'laning: {ADMIN_USERNAME}")
        return

    await message.answer("👋 Xush kelibsiz! Qidiruv yoki qo'shish uchun xabar yozing.")

@router.message(Command("sync"))
async def cmd_sync(message: types.Message):
    status_msg = await message.answer("🔄 **Sinxronlash ketmoqda...**")
    sheet_users = get_all_users_from_sheet()
    
    if not sheet_users:
        await status_msg.edit_text("❌ Sheetdan ma'lumot o'qib bo'lmadi.")
        return

    count = 0
    for row in sheet_users:
        try:
            if len(row) < 3: continue
            user_id, perm_val = row[0], str(row[2]).lower().strip()
            status = 1 if perm_val in ['1', 'true', 'ha', 'bor'] else 0
            db.update_user_permission(user_id, status)
            count += 1
        except: continue

    await status_msg.edit_text(f"✅ Bajarildi! {count} ta user yangilandi.")

# --- CALLBACK HANDLERS (Tugmalar bosilganda) ---

@router.callback_query(F.data.startswith("search:"))
async def process_search_pages(callback: types.CallbackQuery):
    _, query, offset = callback.data.split(":")
    offset = int(offset)
    results = db.search_remnants(query)
    
    text = format_search_results(results[offset:offset+5], len(results), offset)
    kb = get_search_keyboard(query, offset, len(results))
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "confirm_add", AddState.waiting_confirm)
async def confirm_add(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item = data['new_item']
    new_qty = data['current_qty'] + item['qty']
    
    # Bazada va Sheetda yangilash (Sheet funksiyasini sync_remnant_from_sheet dan foydalansa bo'ladi)
    db.update_qty(data['existing_id'], new_qty)
    
    await callback.message.edit_text(f"✅ Dublikatga qo'shildi! Jami: **{new_qty}** ta.", parse_mode="Markdown")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_add", AddState.waiting_confirm)
async def cancel_add(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Amaliyot becolor qilindi.")
    await state.clear()
    await callback.answer()

# --- ASOSIY MATNLI XABARLAR (AI TAHLILI) ---

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    if message.text.startswith('/'): return

    # Ruxsat tekshirish
    db_user = db.get_or_create_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    if not db_user or db_user.get('can_search') == 0:
        await message.answer(f"⛔️ Ruxsat yo'q. Admin: {ADMIN_USERNAME}")
        return

    ai_result = await analyze_message(message.text)
    if not ai_result or ai_result.get('cmd') == 'error':
        await message.answer("❌ Tushunmadim, aniqroq yozing.")
        return

    cmd = ai_result.get('cmd')

    # --- QIDIRISH (SEARCH) ---
    if cmd == 'search':
        query = ai_result.get('query')
        results = db.search_remnants(query)
        if not results:
            await message.answer(f"🤷‍♂️ '{query}' bo'yicha hech narsa topilmadi.")
            return

        text = format_search_results(results[:5], len(results), 0)
        kb = get_search_keyboard(query, 0, len(results))
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")

    # --- QO'SHISH (BATCH ADD) ---
    elif cmd == 'batch_add':
        if db_user.get('can_add') == 0:
            await message.answer("🚫 Sizda qo'shish huquqi yo'q.")
            return

        items = ai_result.get('items', [])
        for item in items:
            # Dublikat tekshirish
            existing = db.check_duplicate(item['material'], item['width'], item['height'], item['location'])
            
            if existing:
                await state.set_state(AddState.waiting_confirm)
                await state.update_data(new_item=item, existing_id=existing['id'], current_qty=existing['qty'])
                
                kb = InlineKeyboardBuilder()
                kb.button(text="✅ Ha, qo'shilsin", callback_data="confirm_add")
                kb.button(text="❌ Bekor qilish", callback_data="cancel_add")
                
                await message.answer(
                    f"⚠️ **Dublikat!**\nOmborda {item['material']} ({item['width']}x{item['height']}) bor.\n"
                    f"Hozirgi soni: {existing['qty']}. Yana {item['qty']} ta qo'shilsinmi?",
                    reply_markup=kb.as_markup(), parse_mode="Markdown"
                )
            else:
                # Yangi qo'shish
                new_id = db.add_remnant_final(item, message.from_user.id, message.from_user.full_name)
                if new_id:
                    sync_new_remnant({'id': new_id, **item, 'user_id': message.from_user.id, 'user_name': message.from_user.full_name})
                    await message.answer(f"✅ Saqlandi: {item['material']} (#{new_id})")
