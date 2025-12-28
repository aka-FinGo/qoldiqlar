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
    if message.text.startswith('/'):
        return

    user = db.get_or_create_user(
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.username
    )

    if not db_user or db_user.get("can_add", 0) == 0:
        return await message.answer(f"⛔️ Ruxsat yo‘q. Admin: {ADMIN_USERNAME}")

    ai = await analyze_message(message.text)

    # === 🔥 FALLBACK LOGIC ===
    if not ai or ai.get("cmd") not in ["add", "batch_add"]:
        if re.search(r'\d+\s*[x×*]\s*\d+', message.text):
            ai = {
                "cmd": "add",
                "items": [{
                    "category": "Boshqa",
                    "material": message.text,
                    "width": 0,
                    "height": 0,
                    "qty": 1,
                    "order": "",
                    "location": ""
                }]
        else:
            return  # qidiruvga o‘tsin

    items = ai.get("items", [])
    if not items:
        return await message.answer("❌ Qo‘shish uchun ma’lumot topilmadi.")

    report = "✅ <b>Qoldiq qo‘shildi:</b>\n\n"

    for item in items:
        # === NORMALIZATSIYA ===
        item["qty"] = int(item.get("qty") or 1)
        item["order"] = item.get("order") or item.get("origin_order") or ""
        item["location"] = item.get("location") or "Sex"

        new_id = db.add_remnant_final(
            item,
            message.from_user.id,
            message.from_user.full_name
        )

        if new_id:
            sync_new_remnant({
                "id": new_id,
                **item,
                "user_id": message.from_user.id,
                "user_name": message.from_user.full_name
            })

            report += (
                f"🆔 #{new_id}\n"
                f"📐 {item.get('width')}x{item.get('height')} | "
                f"📦 {item.get('qty')} ta\n"
                f"📍 {item.get('location')}\n\n"
            )

    await message.answer(report, parse_mode="HTML")

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
