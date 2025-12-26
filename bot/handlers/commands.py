import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder # Bu import kerak
import database.queries as db
from config import ADMIN_ID, ADMIN_USERNAME
from services.gsheets import get_all_users_from_sheet, get_all_remnants_from_sheet
from .utils import format_search_results, get_search_keyboard

router = Router()

# --- 1. START BUYRUG'I ---
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    db.get_or_create_user(user.id, user.full_name, user.username)
    await message.answer(
        f"👋 <b>Assalomu alaykum, {user.full_name}!</b>\n\n"
        "Men mebel qoldiqlarini boshqarishga yordam beraman.\n"
        "Qidirish uchun material nomi yoki o'lchamini yozing.\n"
        "Masalan: <i>'Oq ldsp'</i> yoki <i>'200x300 detal bormi?'</i>\n\n"
        "Yordam uchun: /help", 
        parse_mode="HTML"
    )

# --- 2. HELP (YORDAM) - YANGI QO'SHILDI ---
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "🤖 <b>Botdan foydalanish yo'riqnomasi:</b>\n\n"
        "🔎 <b>Qidiruv:</b>\n"
        "• Shunchaki yozing: <i>'Oq xdf'</i>, <i>'Mdf qora'</i>\n"
        "• O'lcham bo'yicha: <i>'200x500 detal kessa bo'ladimi?'</i>\n\n"
        "📋 <b>Buyruqlar:</b>\n"
        "/list - Barcha mavjud qoldiqlarni ko'rish\n"
        "/ishlatilganlar - Ishlatib bo'lingan qoldiqlar tarixi\n"
        "/men_ishlatganlarim - O'zingiz ishlatgan qoldiqlar\n"
        "/start - Botni qayta ishga tushirish"
    )
    await message.answer(text, parse_mode="HTML")

# --- 3. RO'YXATLAR ---
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
    if not items:
        return await message.answer("📭 Ishlatilgan qoldiqlar tarixi bo'sh.")
    
    text = "📂 <b>Barcha ishlatilgan qoldiqlar:</b>\n\n"
    text += format_search_results(items[:10], len(items), 0) # Oxirgi 10 tasi
    await message.answer(text, parse_mode="HTML")

@router.message(Command("men_ishlatganlarim"))
async def cmd_my_used(message: types.Message):
    items = db.get_used_remnants(user_id=message.from_user.id)
    if not items:
        return await message.answer("📭 Siz hali hech qanday qoldiq ishlatmagansiz.")
    
    text = "👤 <b>Siz ishlatgan qoldiqlar:</b>\n\n"
    text += format_search_results(items[:10], len(items), 0)
    await message.answer(text, parse_mode="HTML")

# --- 4. SINXRONLASH (FONDA) ---
@router.message(Command("sync"))
async def cmd_sync(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID): return
    await message.answer("🔄 <b>Sinxronlash fon rejimida boshlandi...</b>", parse_mode="HTML")
    asyncio.create_task(run_background_sync(message))

async def run_background_sync(message):
    try:
        users = get_all_users_from_sheet()
        for row in users:
            try: db.update_user_permission(row[0], 1 if str(row[2]).lower() in ['1', 'true', 'ha', 'bor'] else 0)
            except: continue
            
        remnants = get_all_remnants_from_sheet()
        for r in remnants:
            try:
                # Skrinshotga mos indekslar:
                # A(0)=ID, D(3)=Mat, E(4)=H, F(5)=W, G(6)=Qty, H(7)=Order, K(10)=Loc, L(11)=Status
                db.sync_remnant_from_sheet(
                    r[0], r[3], int(r[4]), int(r[5]), int(r[6]), 
                    r[7],  # Order (H ustuni)
                    r[10], # Location (K ustuni)
                    int(r[11]) # Status (L ustuni)
                )
            except: continue
        await message.answer("✅ <b>Sinxronlash muvaffaqiyatli yakunlandi!</b>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

# --- 5. VIEW (KO'RISH) ---
@router.message(F.text.startswith("/view_"))
async def cmd_view_detail(message: types.Message):
    try:
        r_id = int(message.text.split("_")[1])
        item = db.get_remnant_details(r_id)
        if not item: return await message.answer("❌ Ma'lumot topilmadi.")

        # Xatolikni oldini olish uchun o'zgaruvchilarni tashqarida olamiz
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
            # Qaytarish logikasi
            used_by = str(item.get('used_by', ''))
            current_user = str(message.from_user.id)
            if used_by == current_user or current_user == str(ADMIN_ID):
                kb.button(text="🔄 Qaytarib qo'yish", callback_data=f"restore:{item['id']}")
        
        await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception as e: print(f"View error: {e}")
