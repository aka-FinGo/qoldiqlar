from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.ai_core import analyze_message
import database.queries as db
from config import ADMIN_ID, ADMIN_USERNAME
from services.gsheets import sync_new_remnant
from .utils import format_search_results, get_search_keyboard

router = Router()

class AddState(StatesGroup):
    waiting_confirm = State()

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext, bot: Bot):
    if message.text.startswith('/'): return

    db_user = db.get_or_create_user(message.from_user.id, message.from_user.full_name, message.from_user.username)
    if not db_user or db_user.get('can_search') == 0:
        return await message.answer(f"⛔️ Ruxsat yo'q. Admin: {ADMIN_USERNAME}")

    ai_result = await analyze_message(message.text)
    if not ai_result or ai_result.get('cmd') == 'error':
        return await message.answer("❓ Tushunarsiz so'rov.")

    cmd = ai_result.get('cmd')
    
    if cmd == 'search':
        req = ai_result.get('requirements', {})
        q_text = ai_result.get('query', '')
        results = db.smart_search(q_text, req.get('min_width', 0), req.get('min_height', 0), req.get('is_flexible', False))
        
        if not results: return await message.answer(f"🤷‍♂️ '{q_text}' topilmadi.")

        text = f"🔍 <b>Natijalar:</b> (Jami: {len(results)})\n"
        text += format_search_results(results[:5], len(results), 0)
        kb = get_search_keyboard(q_text, 0, len(results))
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

    elif cmd == 'batch_add':
        # Batch add mantiqi (avvalgi kodingiz bilan bir xil)
        pass
