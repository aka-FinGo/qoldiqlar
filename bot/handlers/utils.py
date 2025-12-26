from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_search_keyboard(query, offset, total_results):
    builder = InlineKeyboardBuilder()
    if offset >= 5:
        builder.button(text="⬅️ Orqaga", callback_data=f"search:{query}:{max(0, offset-5)}")
    if offset + 5 < total_results:
        builder.button(text="Oldinga ➡️", callback_data=f"search:{query}:{offset+5}")
    builder.adjust(2)
    return builder.as_markup()

def format_search_results(items, total, offset):
    text = f"🔍 <b>Natijalar:</b> (Jami: {total})\n\n"
    for i, item in enumerate(items, 1):
        item_id = item['id']
        cat = str(item.get('category', ''))
        mat = str(item.get('material', ''))
        loc = str(item.get('location', ''))
        text += (f"{offset + i}. <b>{cat} {mat}</b>\n"
                 f"📏 {item['width']}x{item['height']} | 📦 {item['qty']} ta\n"
                 f"📍 {loc} | /view_{item_id}\n"
                 f"----------------------------\n")
    return text
