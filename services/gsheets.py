import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, CREDENTIALS_PATH
from datetime import datetime

def get_sheet_client():
    """Google Sheetga ulanish funksiyasi"""
    # Google Drive va Sheets API ruxsatlari
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # CREDENTIALS_PATH bu config.py dan kelayotgan fayl yo'li (/etc/secrets/credentials.json)
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"❌ GSheets ulanish xatosi: {e}")
        return None

def sync_new_remnant(data):
    """
    Yangi qoldiqni Google Sheetga yozish.
    'data' bu bazadan qaytgan va qo'shimcha ma'lumotlar qo'shilgan lug'at (dict).
    """
    client = get_sheet_client()
    if not client:
        print("⚠️ Sheetga ulanib bo'lmadi, ma'lumot yozilmadi.")
        return

    try:
        # Sheet ID orqali jadvalni ochamiz
        # Agar ID xato bo'lsa, shu yerda xatolik beradi
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # 1-sahifani (List 1) tanlaymiz
        sheet = spreadsheet.sheet1 
        
        # Hozirgi vaqtni chiroyli formatlaymiz (25.12.2025 14:30)
        hozirgi_vaqt = datetime.now().strftime("%d.%m.%Y %H:%M")

        # --- USTUNLAR TARTIBI (Jadvalingiz bilan bir xil bo'lishi shart!) ---
        # 1. ID | 2. Sana | 3. Kategoriya | 4. Material | 5. Bo'yi | 6. Eni | 
        # 7. Soni | 8. Buyurtma | 9. Kim | 10. User ID | 11. Joy | 12. Status | 13. Rasm
        
        row = [
            f"#{data.get('id', 0)}",           # A ustun: ID
            hozirgi_vaqt,                      # B ustun: Sana
            data.get('category', ''),          # C ustun: Kategoriya
            data.get('material', ''),          # D ustun: Material
            data.get('width', 0),              # E ustun: Bo'yi
            data.get('height', 0),             # F ustun: Eni
            data.get('qty', 1),                # G ustun: Soni
            data.get('origin_order', ''),      # H ustun: Buyurtma
            data.get('user_name', ''),         # I ustun: Kim kiritdi
            str(data.get('user_id', '')),      # J ustun: User ID
            data.get('location', ''),          # K ustun: Lokatsiya
            "Mavjud",                          # L ustun: Status
            ""                                 # M ustun: Rasm ID (Hozircha bo'sh)
        ]
        
        # Ma'lumotni oxirgi qatorga qo'shish
        sheet.append_row(row)
        print(f"✅ Google Sheetga yozildi: ID #{data.get('id')}")
        
    except Exception as e:
        print(f"❌ Sheetga yozishda xatolik: {e}")

# Sinov uchun funksiya (Faqat test payti ishlatiladi)
if __name__ == "__main__":
    print("Test boshlandi...")
    test_data = {
        "id": 999,
        "category": "Test",
        "material": "Sinov Material",
        "width": 100,
        "height": 200,
        "qty": 5,
        "origin_order": "Test_Zakaz",
        "user_name": "Admin",
        "user_id": 1234567,
        "location": "Test Joy"
    }
    sync_new_remnant(test_data)
