import asyncio
from aiogram import Router, types, F, Bot
import database.queries as db
from config import ADMIN_ID
from services.gsheets import update_sheet_status
from .utils import format_search_results, get_search_keyboard

router = Router()

@router.callback_query(F.data.startswith("search:"))
async def process_search_pages(callback: types.CallbackQuery):
    _, query, offset = callback.data.split(":")
    offset = int(offset)
    results = db.get_all_active_remnants() if query == "ALL_LIST" else db.search_remnants(query)
    
    if not results: return await callback.answer("Natija yo'q")
    
    text = format_search_results(results[offset:offset+5], len(results), offset)
    kb = get_search_keyboard(query, offset, len(results))
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("use:"))
async def process_use(callback: types.CallbackQuery, bot: Bot):
    r_id = int(callback.data.split(":")[1])
    success = db.use_remnant(r_id, callback.from_user.id)
    if success:
        # Google Sheetni fonda yangilash (bot qotib qolmasligi uchun)
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, update_sheet_status, r_id, 0)
        
        await callback.message.edit_text(f"📉 <b>ID #{r_id}</b> ishlatilgan deb belgilandi.", parse_mode="HTML")
        if str(callback.from_user.id) != str(ADMIN_ID):
            await bot.send_message(ADMIN_ID, f"📉 Qoldiq ishlatildi: #{r_id}\nKim: {callback.from_user.full_name}")
    else:
        await callback.answer("❌ Bu qoldiq allaqachon ishlatilgan.", show_alert=True)

@router.callback_query(F.data.startswith("restore:"))
async def process_restore(callback: types.CallbackQuery):
    r_id = int(callback.data.split(":")[1])
    if db.restore_remnant(r_id):
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, update_sheet_status, r_id, 1)
        await callback.message.edit_text(f"🔄 ID #{r_id} omborga qaytarildi.")
    await callback.answer()
