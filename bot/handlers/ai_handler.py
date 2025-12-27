from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.ai_core import analyze_message
import database.queries as db
from config import ADMIN_ID, ADMIN_USERNAME
from services.gsheets import sync_new_remnant
from .utils import format_search_results, get_search_keyboard
from services.search_engine import perform_smart_search

router = Router()

class AddState(StatesGroup):
    waiting_confirm = State()

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext, bot: Bot):
    if message.text.startswith('/'): return

    # 1. FOYDALANUVCHI RUXSATINI TEKSHIRISH
    db_user = db.get_or_create_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    
    # Logdagi 'tuple' xatosini oldini olish uchun indeks orqali tekshiramiz
    # db_user[3] - can_search ustuni (bazadagi tartibga qarab)
    # Agar queries.py da SELECT * bo'lsa, can_search odatda 3-indeksda bo'ladi.
    if not db_user or (len(db_user) > 3 and db_user[3] == 0):
        return await message.answer(f"⛔️ Kechirasiz, sizga ruxsat berilmagan. Admin: {ADMIN_USERNAME}")

    # AI orqali matnni tahlil qilish
    ai_result = await analyze_message(message.text)
    
    if not ai_result or ai_result.get('cmd') == 'error':
        ai_result = {"cmd": "search", "keywords": message.text.split()}

    cmd = ai_result.get('cmd')
    
    # --- 🔍 QIDIRUV BLOKI ---
    if cmd == 'search':
        # Smart search funksiyasini chaqiramiz
        results = perform_smart_search(message.text)
        
        if not results:
            return await message.answer("🔍 Hech narsa topilmadi. O'lcham yoki materialni aniqroq yozing.")

        # Natijalarni formatlash (Tuple'dan chiroyli matnga)
        response_text = "<b>🔍 Topilgan qoldiqlar:</b>\n\n"
        for r in results:
            # r[0]-id, r[1]-cat, r[2]-mat, r[3]-w, r[4]-h, r[5]-qty
            status = "✅" if r[8] == 1 else "🔴"
            response_text += (
                f"🆔 <b>#{r[0]}</b> | {r[1]} {r[2]}\n"
                f"📐 {r[3]}x{r[4]} | 📦 {r[5]} dona | {status}\n"
                f"📍 {r[7] or '-'}\n"
                f"-------------------\n"
            )
        
        # Agar natijalar ko'p bo'lsa, xabarni bo'lib yuborish
        if len(response_text) > 4000:
            for i in range(0, len(response_text), 4000):
                await message.answer(response_text[i:i+4000], parse_mode="HTML")
        else:
            await message.answer(response_text, parse_mode="HTML")

    # --- ➕ QO'SHISH BLOKI ---
    elif cmd == 'add':
        items = ai_result.get('items', [])
        if not items:
            return await message.answer("❌ Qoldiq ma'lumotlarini aniqlay olmadim.")

        report = "🚀 <b>Yangi qoldiqlar bazaga va Sheetga qo'shildi:</b>\n\n"
        for item in items:
            # 1. Bazaga yozish va yangi ID ni olish
            new_id = db.add_remnant_final(item, message.from_user.id, message.from_user.full_name)
            
            if new_id:
                # 2. GSheetga yozish (ID bilan birga)
                # Diqqat: tartib A-Q bo'lishi uchun data obyektini to'liq yuboramiz
                sync_data = {
                    'id': new_id,
                    'category': item.get('category'),
                    'material': item.get('material'),
                    'width': item.get('width'),
                    'height': item.get('height'),
                    'qty': item.get('qty'),
                    'order': item.get('order'),
                    'location': item.get('location'),
                    'user_id': message.from_user.id,
                    'user_name': message.from_user.full_name
                }
                sync_new_remnant(sync_data)
                
                report += (f"✅ <b>#{new_id}</b> {item['category']} {item['material']}\n"
                           f"📐 {item['width']}x{item['height']} | 📦 {item['qty']} dona\n\n")
        
        await message.answer(report, parse_mode="HTML")

    
    # --- BATCH ADD (O'zgarishsiz) ---
    elif cmd == 'batch_add':
        items = ai_result.get('items', [])
        if not items: return await message.answer("⚠️ Ma'lumot tushunarsiz.")
        
        report = ""
        for item in items:
            existing = db.check_duplicate(item['material'], item['width'], item['height'], item.get('location', ''))
            
            if existing:
                await state.set_state(AddState.waiting_confirm)
                await state.update_data(new_item=item, existing_id=existing['id'], current_qty=existing['qty'])
                
                kb = InlineKeyboardBuilder()
                kb.button(text="✅ Ha, qo'shilsin", callback_data="confirm_add")
                kb.button(text="❌ Bekor qilish", callback_data="cancel_add")
                kb.adjust(2)
                
                await message.answer(
                    f"⚠️ <b>Dublikat topildi!</b>\n📦 {item['material']} ({item['width']}x{item['height']})\n"
                    f"💾 Omborda: {existing['qty']} ta. Yana {item['qty']} ta qo'shilsinmi?",
                    reply_markup=kb.as_markup(), parse_mode="HTML"
                )
                return 

            else:
                new_id = db.add_remnant_final(item, message.from_user.id, message.from_user.full_name)
                if new_id:
                    sync_new_remnant({'id': new_id, **item, 'user_id': message.from_user.id, 'user_name': message.from_user.full_name})
                    report += (f"✅ <b>#{new_id}</b> {item['category']} {item['material']}\n"
                               f"📏 {item['width']}x{item['height']} | 🔢 {item.get('order', '-')}\n\n")
        
        if report: await message.answer(report, parse_mode="HTML")

# --- Callbacks o'zgarishsiz qoladi ---
@router.callback_query(F.data == "confirm_add", AddState.waiting_confirm)
async def process_confirm_add(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item = data.get('new_item')
    new_id = db.add_remnant_final(item, callback.from_user.id, callback.from_user.full_name)
    if new_id:
        sync_new_remnant({'id': new_id, **item, 'user_id': callback.from_user.id, 'user_name': callback.from_user.full_name})
        await callback.message.edit_text(f"✅ Qo'shildi: #{new_id}")
    await state.clear()

@router.callback_query(F.data == "cancel_add", AddState.waiting_confirm)
async def process_cancel_add(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Bekor qilindi.")
    await state.clear()
