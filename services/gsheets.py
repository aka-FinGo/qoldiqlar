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
        # Secret File orqali ulanish
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"❌ GSheets ulanish xatosi: {e}")
        return None

# --- 1. QOLDIQLARNI YOZISH (1-SAHIFA) ---
def sync_new_remnant(data):
    """Yangi qoldiqni 'Qoldiqlar' (index 0) sahifasiga yozish"""
    client = get_sheet_client()
    if not client: return

    try:
        # 0-indeks bu birinchi sahifa
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
        
        hozirgi_vaqt = datetime.now().strftime("%d.%m.%Y %H:%M")

        # Rasmga asoslangan ustunlar tartibi (A dan Q gacha)
        row = [
            f"#{data.get('id', 0)}",           # A: ID
            hozirgi_vaqt,                      # B: Sana
            data.get('category', ''),          # C: Kategoriya
            data.get('material', ''),          # D: Material
            data.get('width', 0),              # E: Bo'yi
            data.get('height', 0),             # F: Eni
            data.get('qty', 1),                # G: Soni
            data.get('origin_order', ''),      # H: Buyurtma
            data.get('user_name', ''),         # I: Kim (Ismi)
            str(data.get('user_id', '')),      # J: User ID
            data.get('location', ''),          # K: Lokatsiya
            1,                                 # L: Status (1=Mavjud)
            "",                                # M: Rasm ID
            # --- Ishlatilganda to'ldiriladigan (Hozircha bo'sh) ---
            "", "", "", ""                     # N, O, P, Q
        ]
        
        sheet.append_row(row)
        print(f"✅ Qoldiq Sheetga yozildi: #{data.get('id')}")
        
    except Exception as e:
        print(f"❌ Qoldiqni yozishda xatolik: {e}")

# --- 2. USERLARNI YOZISH (2-SAHIFA) ---
def sync_new_user(user_id, full_name):
    """Yangi userni 'Ruxsatlar' (index 1) sahifasiga yozish"""
    client = get_sheet_client()
    if not client: return

    try:
        # 1-indeks bu ikkinchi sahifa
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(1)
        
        # Takrorlanmasligi uchun tekshiramiz (A ustun - ID lar)
        try:
            existing_ids = sheet.col_values(1) 
            if str(user_id) in existing_ids:
                return # User allaqachon bor, qayta yozmaymiz
        except:
            pass 

        # --- 2-RASM ASOSIDA TARTIB ---
        # A: ID | B: Ism | C: Qidirish | D: Qo'shish | E: Tahrir | F: O'chirish | G: Ishlatish
        # HAMMA RUXSATLAR "0" (Admin ruxsat bermaguncha)
        row = [
            str(user_id),  # A: User ID
            full_name,     # B: Ismi
            0,             # C: Qidirish (YO'Q)
            0,             # D: Qoshish (YO'Q)
            0,             # E: Tahrirlash (YO'Q)
            0,             # F: Ochirish (YO'Q)
            0              # G: Ishlatish (YO'Q)
        ]
        
        sheet.append_row(row)
        print(f"✅ Yangi User Sheetga (Ruxsatsiz) qo'shildi: {full_name}")
        
    except Exception as e:
        print(f"❌ Userni yozishda xatolik: {e}")
