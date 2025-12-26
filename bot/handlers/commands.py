import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
import database.queries as db
from config import ADMIN_ID, ADMIN_USERNAME
from services.gsheets import get_all_users_from_sheet, get_all_remnants_from_sheet
from .utils import format_search_results, get_search_keyboard # Yordamchi funksiyalar

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    db_user = db.get_or_create_user(user.id, user.full_name, user.username)
    await message.answer("👋 Xush kelibsiz! Material qidirish yoki qo'shish uchun xabar yozing.")

@router.message(Command("list"))
async def cmd_list_all(message: types.Message):
    items = db.get_all_active_remnants()
    if not items:
        return await message.answer("📭 Omborda qoldiq mavjud emas.")
    
    text = f"📋 <b>Mavjud qoldiqlar</b> (Jami: {len(items)} ta):\n\n"
    text += format_search_results(items[:5], len(items), 0)
    kb = get_search_keyboard("ALL_LIST", 0, len(items))
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(Command("sync"))
async def cmd_sync(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID): return
    
    await message.answer("🔄 <b>Sinxronlash fon rejimida boshlandi...</b>\nBot ishlashda davom etadi.", parse_mode="HTML")
    
    # MUAMMO YECHIMI: Fon rejimida ishga tushirish (asyncio.create_task)
    asyncio.create_task(run_background_sync(message))

async def run_background_sync(message):
    try:
        users = get_all_users_from_sheet()
        for row in users:
            try: db.update_user_permission(row[0], 1 if str(row[2]).lower() in ['1', 'true', 'ha'] else 0)
            except: continue
            
        remnants = get_all_remnants_from_sheet()
        for r in remnants:
            try:
                db.sync_remnant_from_sheet(r[0], r[3], int(r[4]), int(r[5]), int(r[6]), r[9], r[10], int(r[11]))
            except: continue
        
        await message.answer("✅ <b>Sinxronlash muvaffaqiyatli yakunlandi!</b>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Sinxronlashda xato: {e}")

@router.message(F.text.startswith("/view_"))
async def cmd_view_detail(message: types.Message):
    try:
        r_id = int(message.text.split("_")[1])
        item = db.get_remnant_details(r_id)
        if not item: return await message.answer("❌ Ma'lumot topilmadi.")

        text = (f"📑 <b>Ma'lumot (ID: #{item['id']})</b>\n\n"
                f"🛠 <b>Material:</b> {item['category']} {item['material']}\n"
                f"📏 <b>O'lcham:</b> {item['width']}x{item['height']} mm\n"
                f"📦 <b>Soni:</b> {item['qty']} ta\n")
        
        kb = InlineKeyboardBuilder()
        if item['status'] == 1:
            kb.button(text="✅ Ishlatish (Olish)", callback_data=f"use:{item['id']}")
        else:
            kb.button(text="🔄 Qaytarib qo'yish", callback_data=f"restore:{item['id']}")
        
        await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except: pass
