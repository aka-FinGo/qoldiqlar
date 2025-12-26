from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.ai_core import analyze_message
import database.queries as db
from config import ADMIN_ID, ADMIN_USERNAME
from services.gsheets import sync_new_remnant
from .utils import format_search_results, get_search_keyboard

# YANGI: Aqlli qidiruv motorini import qilamiz
# (Bu ishlashi uchun services/search_engine.py fayli bo'lishi shart)
from services.search_engine import perform_smart_search

router = Router()

# FSM (Holatlar) - Dublikatni tasdiqlash uchun
class AddState(StatesGroup):
    waiting_confirm = State()

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext, bot: Bot):
    if message.text.startswith('/'): return

    # 1. Foydalanuvchini tekshirish
    db_user = db.get_or_create_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    if not db_user or db_user.get('can_search') == 0:
        return await message.answer(f"⛔️ Ruxsat yo'q. Admin: {ADMIN_USERNAME}")

    # 2. AI tahlili
    ai_result = await analyze_message(message.text)
    
    if not ai_result or ai_result.get('cmd') == 'error':
        # Agar AI tushunmasa, shunchaki matn bo'yicha qidirib ko'ramiz
        ai_result = {"cmd": "search", "keywords": message.text.split()}

    cmd = ai_result.get('cmd')
    
    # --- 1. AQLLI QIDIRUV BLOKI ---
    if cmd == 'search':
        # AIdan kelgan parametrlarni tayyorlaymiz
        keywords = ai_result.get('keywords', [])
        
        # Agar keywords bo'sh bo'lsa, lekin query bo'lsa (eski format), uni olamiz
        if not keywords and ai_result.get('query'):
            keywords = ai_result.get('query').split()

        params = {
            "keywords": keywords,
            "min_w": ai_result.get('min_w', 0),
            "min_h": ai_result.get('min_h', 0)
        }

        # Alohida fayldan qidiruvni chaqiramiz
        results = perform_smart_search(params)
        
        if not results:
            await message.answer("🤷‍♂️ So'rovingiz bo'yicha mos material topilmadi.")
            return

        # Natijalarni chiqarish
        query_str = " ".join(keywords) if keywords else "Natijalar"
        text = f"🔍 <b>Topildi:</b> (Jami: {len(results)})\n"
        if params['min_w']:
            text += f"📏 O'lcham: {params['min_w']}x{params['min_h']} (aylantirib ham)\n"
        
        text += format_search_results(results[:5], len(results), 0)
        kb = get_search_keyboard(query_str, 0, len(results))
        
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

    # --- 2. BATCH ADD (Qo'shish va Dublikat tekshirish) ---
    elif cmd == 'batch_add':
        items = ai_result.get('items', [])
        if not items:
            return await message.answer("⚠️ Ma'lumotlarni to'liq ajratib bo'lmadi.")
        
        report = ""
        
        for item in items:
            # 2.1 Dublikat tekshiruvi
            # Bazada shunday material, o'lcham va joylashuv borligini tekshiramiz
            # (queries.py da check_duplicate funksiyasi bo'lishi kerak)
            existing = db.check_duplicate(item['material'], item['width'], item['height'], item.get('location', ''))
            
            if existing:
                # AGAR BOR BO'LSA: FSM holatiga o'tamiz va tugma chiqaramiz
                await state.set_state(AddState.waiting_confirm)
                # Ma'lumotni vaqtinchalik xotiraga yozamiz
                await state.update_data(new_item=item, existing_id=existing['id'], current_qty=existing['qty'])
                
                kb = InlineKeyboardBuilder()
                kb.button(text="✅ Ha, qo'shilsin", callback_data="confirm_add")
                kb.button(text="❌ Bekor qilish", callback_data="cancel_add")
                kb.adjust(2)
                
                await message.answer(
                    f"⚠️ <b>Dublikat topildi!</b>\n\n"
                    f"📦 {item['material']} ({item['width']}x{item['height']})\n"
                    f"📍 Joy: {item.get('location', '-')}\n"
                    f"💾 Omborda bor: <b>{existing['qty']} ta</b>\n\n"
                    f"Yana <b>{item['qty']} ta</b> qo'shilsinmi?",
                    reply_markup=kb.as_markup(),
                    parse_mode="HTML"
                )
                return # Tsiklni to'xtatamiz, user javobini kutamiz

            else:
                # 2.2 Dublikat yo'q -> Darhol qo'shamiz
                new_id = db.add_remnant_final(item, message.from_user.id, message.from_user.full_name)
                if new_id:
                    # GSheetsga yozish (order va location bilan)
                    sync_new_remnant({
                        'id': new_id, 
                        **item, 
                        'user_id': message.from_user.id, 
                        'user_name': message.from_user.full_name
                    })
                    report += (f"✅ <b>#{new_id}</b> {item['category']} {item['material']}\n"
                               f"📏 {item['width']}x{item['height']} | 🔢 Zakaz: {item.get('order', '-')}\n"
                               f"📍 {item.get('location', '-')}\n\n")
        
        if report:
            await message.answer(report, parse_mode="HTML")

# --- 3. CALLBACK HANDLERS (Dublikatni tasdiqlash uchun) ---

@router.callback_query(F.data == "confirm_add", AddState.waiting_confirm)
async def process_confirm_add(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    item = data.get('new_item')
    
    # Bazaga qo'shish
    new_id = db.add_remnant_final(item, callback.from_user.id, callback.from_user.full_name)
    
    if new_id:
        # GSheetsga yozish
        sync_new_remnant({
            'id': new_id, 
            **item, 
            'user_id': callback.from_user.id, 
            'user_name': callback.from_user.full_name
        })
        
        await callback.message.edit_text(
            f"✅ <b>Qo'shildi!</b> (Dublikat tasdiqlandi)\n"
            f"🆔 ID: #{new_id}\n"
            f"📦 {item['material']} - {item['qty']} ta",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text("❌ Xatolik yuz berdi.")
        
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_add", AddState.waiting_confirm)
async def process_cancel_add(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Qo'shish bekor qilindi.")
    await state.clear()
    await callback.answer()
