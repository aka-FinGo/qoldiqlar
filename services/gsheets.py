import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, CREDENTIALS_PATH
from datetime import datetime

def get_sheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"❌ GSheets ulanish xatosi: {e}")
        return None

def sync_new_remnant(data):
    """Yangi qoldiqni Sheetga skrinshot va J-Q tartibiga moslab yozish"""
    client = get_sheet_client()
    if not client: return
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
        hozirgi_vaqt = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Ustunlar tartibi (A-Q):
        row = [
            f"#{data.get('id')}",           # A: ID
            hozirgi_vaqt,                    # B: SANA
            data.get('category'),           # C: Kategoriya
            data.get('material'),           # D: Material
            data.get('height'),             # E: Bo'yi
            data.get('width'),              # F: Eni
            data.get('qty'),                # G: Soni
            data.get('order'),              # H: Buyurtma (Zakaz)
            data.get('user_name'),          # I: Kim qo'shdi
            str(data.get('user_id')),       # J: User ID
            data.get('location'),           # K: Lokatsiya/Izoh
            1,                              # L: Status (1-mavjud)
            "",                             # M: Rasm ID (bo'sh)
            "",                             # N: Kim oldi
            "",                             # O: Olingan sana
            "",                             # P: Qaysi zakazga
            ""                              # Q: Sabab
        ]
        sheet.append_row(row)
        print(f"✅ Sheetga qo'shildi: #{data.get('id')}")
    except Exception as e: 
        print(f"❌ Sheetga yozishda xato: {e}")


def sync_new_user(user_id, full_name):
    """Yangi userni Ruxsatlar varag'iga yozish"""
    client = get_sheet_client()
    if not client: return
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(1)
        if str(user_id) not in sheet.col_values(1):
            sheet.append_row([str(user_id), full_name, 0, 0, 0, 0, 0])
    except Exception as e: print(f"❌ Userni sheetga yozishda xato: {e}")

def get_all_users_from_sheet():
    """Ruxsatlarni o'qish (2-sahifa)"""
    client = get_sheet_client()
    if not client: return []
    try:
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(1).get_all_values()[1:]
    except: return []

def get_all_remnants_from_sheet():
    """Qoldiqlarni o'qish (1-sahifa)"""
    client = get_sheet_client()
    if not client: return []
    try:
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(0).get_all_values()[1:]
    except: return []

# services/gsheets.py fayliga qo'shing

def update_sheet_qty(remnant_id, new_qty):
    """G ustunidagi (7-ustun) sonni yangilash"""
    client = get_sheet_client()
    if not client: return
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
        cell = sheet.find(f"#{remnant_id}")
        if cell:
            sheet.update_cell(cell.row, 7, new_qty) # G ustuni (7-ustun)
    except Exception as e:
        print(f"❌ Qty yangilashda xato: {e}")



def update_sheet_status(remnant_id, status):
    """L ustunidagi (12-ustun) holatni yangilash"""
    client = get_sheet_client()
    if not client: return
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
        cell = sheet.find(f"#{remnant_id}")
        if cell:
            # Status L ustunida (12-ustun)
            sheet.update_cell(cell.row, 12, status)
            print(f"✅ ID #{remnant_id} statusi {status} ga yangilandi.")
    except Exception as e:
        print(f"❌ Status yangilashda xato: {e}")