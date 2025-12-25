import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, CREDENTIALS_PATH
from datetime import datetime

def get_sheet_client():
    """Google Sheetga ulanish"""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"❌ GSheets ulanish xatosi: {e}")
        return None

def sync_new_remnant(data):
    """
    Yangi qoldiq qo'shilganda Sheetga yozish (A dan M gacha).
    N, O, P, Q ustunlar bo'sh qoladi (chunki hali ishlatilmadi).
    """
    client = get_sheet_client()
    if not client: return

    try:
        # Sheetni ochamiz
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        
        # Hozirgi vaqt
        hozirgi_vaqt = datetime.now().strftime("%d.%m.%Y %H:%M")

        # --- SIZ YUBORGAN RASM ASOSIDA TARTIB ---
        row = [
            f"#{data.get('id', 0)}",           # A: ID
            hozirgi_vaqt,                      # B: Sana
            data.get('category', ''),          # C: Kategoriya
            data.get('material', ''),          # D: Material
            data.get('width', 0),              # E: Bo'yi (Rasmda E=Bo'yi)
            data.get('height', 0),             # F: Eni  (Rasmda F=Eni)
            data.get('qty', 1),                # G: Soni
            data.get('origin_order', ''),      # H: Buyurtma (Kelib chiqish)
            data.get('user_name', ''),         # I: Kim (Kiritgan odam)
            str(data.get('user_id', '')),      # J: User ID
            data.get('location', ''),          # K: Lokatsiya
            1,                                 # L: Status (1=Mavjud)
            "",                                # M: Rasm ID (Hozircha bo'sh)
            
            # --- ISHLATILGANDA TO'LDIRILADIGAN QISMLAR (Hozircha bo'sh) ---
            "",                                # N: Kim oldi?
            "",                                # O: Sana (Olgan)
            "",                                # P: Zakaz (Yangi)
            ""                                 # Q: Sabab
        ]
        
        sheet.append_row(row)
        print(f"✅ Google Sheetga yangi qator qo'shildi: #{data.get('id')}")
        
    except Exception as e:
        print(f"❌ Sheetga yozishda xatolik: {e}")
