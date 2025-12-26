from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.ai_core import analyze_message
import database.queries as db
from .utils import format_search_results, get_search_keyboard

router = Router()

class AddState(StatesGroup):
    waiting_confirm = State()

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext, bot: Bot):
    if message.text.startswith('/'): return
    
    # AI tahlili
    ai_result = await analyze_message(message.text)
    if not ai_result: return
    
    cmd = ai_result.get('cmd')
    if cmd == 'search':
        # Smart Search mantiqi shu yerda davom etadi...
        pass
    # ... qolgan batch_add kodlari
