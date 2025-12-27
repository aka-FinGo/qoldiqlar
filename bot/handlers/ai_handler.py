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

    db_user = db.get_or_create_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    if not db_user or db_user[1] == 0:
        return await message.answer(f"⛔️ Ruxsat yo'q. Admin: {ADMIN_USERNAME}")

    # AI Tahlil
    ai_result = await analyze_message(message.text)
    
    # Agar AI adashsa yoki bo'sh kelsa
    if not ai_result or ai_result.get('cmd') == 'error':
        ai_result = {"cmd": "search", "keywords": message.text.split()}

    cmd = ai_result.get('cmd')
    
    # --- TUZATILGAN SEARCH BLOKI ---
    if cmd == 'search':
        keywords = ai_result.get('keywords', [])
        min_w = ai_result.get('min_w', 0)
        min_h = ai_result.get('min_h', 0)
        
        # 1. Agar AI keywords bermasa-yu, lekin oddiy query bo'lsa
        if not keywords and ai_result.get('query'):
            keywords = ai_result.get('query').split()

        # 2. XATONI TUZATISH: 
        # Agar o'lcham (min_w, min_h) topilgan bo'lsa, keywords ichidagi 
        # raqamli so'zlarni (masalan "200", "500", "200x500") O'CHIRIB TASHLAYMIZ.
        # Aks holda bot "LDSP 200" deb nom qidirishga tushadi.
        if min_w > 0 or min_h > 0:
            cleaned_keywords = []
            for k in keywords:
                # Agar so'zda raqam qatnashmagan bo'lsa (masalan "Oq", "MDF") olib qolamiz
                if not any(char.isdigit() for char in k):
                    cleaned_keywords.append(k)
            keywords = cleaned_keywords

        params = {
            "keywords": keywords,
            "min_w": min_w,
            "min_h": min_h
        }

        results = perform_smart_search(params)
        
        if not results:
            await message.answer(f"🤷‍♂️ '{message.text}' bo'yicha mos qoldiq topilmadi.")
            return

        # Natija matni
        header_text = " ".join(keywords) if keywords else "O'lcham"
        text = f"🔍 <b>Topildi:</b> (Jami: {len(results)})\n"
        if min_w:
            text += f"📏 {min_w}x{min_h} mm (aylantirib ham)\n"
        
        text += format_search_results(results[:5], len(results), 0)
        kb = get_search_keyboard("SMART_SEARCH", 0, len(results)) # Callback data soddalashtirildi
        
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

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
