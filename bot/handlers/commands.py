import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database.queries as db
from config import ADMIN_ID, ADMIN_USERNAME
from services.gsheets import get_all_users_from_sheet, get_all_remnants_from_sheet
from .utils import format_search_results, get_search_keyboard

router = Router()

# --- 1. START & HELP ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    db.get_or_create_user(user.id, user.full_name, user.username)
    await message.answer(
        f"👋 <b>Assalomu alaykum, {user.full_name}!</b>\n\n"
        "Men mebel qoldiqlarini boshqarishga yordam beraman.\n"
        "Qidirish uchun shunchaki yozing:\n"
        "<i>'Oq ldsp'</i> yoki <i>'200x300 detal bormi?'</i>\n\n"
        "Yordam uchun: /help", 
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "🤖 <b>Botdan foydalanish:</b>\n\n"
        "🔎 <b>Qidiruv:</b>\n"
        "• <i>'Oq xdf'</i> - Material nomi bo'yicha\n"
        "• <i>'200x500'</i> - O'lcham bo'yicha\n"
        "• <i>'150_12'</i> - Zakaz raqami bo'yicha\n\n"
        "📋 <b>Buyruqlar:</b>\n"
        "/list - Barcha qoldiqlar\n"
        "/ishlatilganlar - Tarix\n"
        "/sync - Bazani yangilash (Admin)"
    )
    await message.answer(text, parse_mode="HTML")

# --- 2. LIST COMMANDS ---
@router.message(Command("list"))
async def cmd_list_all(message: types.Message):
    items = db.get_all_active_remnants()
    if not items:
        return await message.answer("📭 Omborda qoldiq mavjud emas.")
    
    text = f"📋 <b>Mavjud qoldiqlar</b> (Jami: {len(items)} ta):\n\n"
    text += format_search_results(items[:5], len(items), 0)
    kb = get_search_keyboard("ALL_LIST", 0, len(items))
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(Command("ishlatilganlar"))
async def cmd_all_used(message: types.Message):
    items = db.get_used_remnants()
    if not items: return await message.answer("📭 Tarix bo'sh.")
    text = "📂 <b>Ishlatilganlar tarixi:</b>\n\n" + format_search_results(items[:10], len(items), 0)
    await message.answer(text, parse_mode="HTML")

@router.message(Command("men_ishlatganlarim"))
async def cmd_my_used(message: types.Message):
    items = db.get_used_remnants(user_id=message.from_user.id)
    if not items: return await message.answer("📭 Siz hali qoldiq ishlatmadingiz.")
    text = "👤 <b>Sizning tarixingiz:</b>\n\n" + format_search_results(items[:10], len(items), 0)
    await message.answer(text, parse_mode="HTML")

# --- 3. SYNC (TUZATILGAN QISM) ---
@router.message(Command("sync"))
async def cmd_sync(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID): return
    await message.answer("🔄 <b>Sinxronlash boshlandi...</b>", parse_mode="HTML")
    asyncio.create_task(run_background_sync(message))

async def run_background_sync(message):
    try:
        # 1. Userlarni yangilash
        users = get_all_users_from_sheet()
        for row in users:
            try: db.update_user_permission(row[0], 1 if str(row[2]).lower() in ['1', 'true', 'ha', 'bor'] else 0)
            except: continue
            
        # 2. Qoldiqlarni yangilash
        remnants = get_all_remnants_from_sheet()
        for r in remnants:
            try:
                # DIQQAT: Indekslar Sheetdagi ustunlarga moslandi (A=0)
                # r[7] -> H ustuni (Buyurtma raqami)
                # r[10] -> K ustuni (Lokatsiya)
                # r[11] -> L ustuni (Status)
                
                db.sync_remnant_from_sheet(
                    r[0],      # ID
                    r[3],      # Material
                    int(r[4]), # Bo'yi
                    int(r[5]), # Eni
                    int(r[6]), # Soni
                    r[7],      # <--- TUZATILDI: H ustuni (Buyurtma)
                    r[10],     # Lokatsiya
                    int(r[11]) # Status
                )
            except Exception as e: 
                print(f"Sync error row: {e}")
                continue
                
        await message.answer("✅ <b>Sinxronlash tugadi!</b>\nMa'lumotlar yangilandi.", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

# --- 4. VIEW DETAIL ---
@router.message(F.text.startswith("/view_"))
async def cmd_view_detail(message: types.Message):
    try:
        r_id = int(message.text.split("_")[1])
        item = db.get_remnant_details(r_id)
        if not item: return await message.answer("❌ Topilmadi.")

        order_val = item.get('origin_order', "Yo'q")
        loc_val = item.get('location', "Noma'lum")

        text = (f"📑 <b>Ma'lumot (ID: #{item['id']})</b>\n\n"
                f"🛠 <b>Material:</b> {item['category']} {item['material']}\n"
                f"📏 <b>O'lcham:</b> {item['width']}x{item['height']} mm\n"
                f"📦 <b>Soni:</b> {item['qty']} ta\n"
                f"🔢 <b>Buyurtma:</b> {order_val}\n"
                f"📍 <b>Joy:</b> {loc_val}")
        
        kb = InlineKeyboardBuilder()
        if item['status'] == 1:
            kb.button(text="✅ Ishlatish (Olish)", callback_data=f"use:{item['id']}")
        else:
            used_by = str(item.get('used_by', ''))
            current_user = str(message.from_user.id)
            if used_by == current_user or current_user == str(ADMIN_ID):
                kb.button(text="🔄 Qaytarib qo'yish", callback_data=f"restore:{item['id']}")
        
        await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except: pass
