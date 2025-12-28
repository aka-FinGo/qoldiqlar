import re
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
import database.queries as db
from services.ai_core import analyze_message
from services.gsheets import sync_new_remnant
from config import ADMIN_USERNAME

router = Router()

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext, bot: Bot):
    if message.text.startswith('/'):
        return

    user = db.get_or_create_user(
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.username
    )

    if not user or user.get("can_add", 0) == 0:
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
