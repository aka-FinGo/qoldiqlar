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

# --- 1. QOLDIQLARNI YOZISH (1-RASM BO'YICHA) ---
def sync_new_remnant(data):
    """Yangi qoldiqni 'Qoldiqlar' (1-sahifa) ga yozish"""
    client = get_sheet_client()
    if not client: return

    try:
        # 1-sahifani (index=0) olamiz. Odatda bu "Qoldiqlar"
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
        
        hozirgi_vaqt = datetime.now().strftime("%d.%m.%Y %H:%M")

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
            # --- Ishlatilganda to'ldiriladigan (bo'sh qoladi) ---
            "", "", "", ""                     # N, O, P, Q
        ]
        
        sheet.append_row(row)
        print(f"✅ Qoldiq Sheetga yozildi: #{data.get('id')}")
        
    except Exception as e:
        print(f"❌ Qoldiqni yozishda xatolik: {e}")

# --- 2. USERLARNI YOZISH (2-RASM BO'YICHA) ---
def sync_new_user(user_id, full_name):
    """Yangi userni 'Ruxsatlar' (2-sahifa) ga yozish"""
    client = get_sheet_client()
    if not client: return

    try:
        # 2-sahifani (index=1) olamiz. Odatda bu "Ruxsatlar"
        # Agar sahifa nomini aniq bilsangiz: .worksheet("Ruxsatlar") deb yozish ham mumkin
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(1)
        
        # Avval bu user borligini tekshiramiz (Takrorlanmasligi uchun)
        # 1-ustun (A) User ID lari
        try:
            existing_ids = sheet.col_values(1) 
            if str(user_id) in existing_ids:
                print(f"ℹ️ User {user_id} Sheetda allaqachon bor.")
                return
        except:
            pass # Agar jadval bo'm-bo'sh bo'lsa, davom etaveramiz

        # --- 2-RASM ASOSIDA TARTIB ---
        # A: User ID | B: Ismi | C: Qidirish | D: Qoshish | E: Tahrirlash | F: Ochirish | G: Ishlatish
        
        row = [
            str(user_id),  # A: User ID
            full_name,     # B: Ismi
            1,             # C: Qidirish (Default: 1 - Ruxsat bor)
            0,             # D: Qoshish (Default: 0 - Ruxsat yo'q)
            0,             # E: Tahrirlash
            0,             # F: Ochirish
            0              # G: Ishlatish
        ]
        
        sheet.append_row(row)
        print(f"✅ Yangi User Sheetga qo'shildi: {full_name}")
        
    except Exception as e:
        print(f"❌ Userni yozishda xatolik: {e}")
