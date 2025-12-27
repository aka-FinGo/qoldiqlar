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
    """Yangi qoldiqni Sheetga A-Q tartibiga 100% moslab yozish"""
    client = get_sheet_client()
    if not client: return
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
        hozirgi_vaqt = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # ID ni tekshiramiz (data ichida 'id' borligiga ishonch hosil qiling)
        new_id = data.get('id')
        if not new_id:
            print("⚠️ Xato: ID topilmadi, Sheetga yozilmadi.")
            return

        # A-Q TARTIBI (17 TA USTUN):
        row = [
            f"#{new_id}",                   # A: id (ID endi aniq chiqadi)
            data.get('category', ''),       # B: category
            data.get('material', ''),       # C: material
            data.get('width', 0),           # D: width
            data.get('height', 0),          # E: height
            data.get('qty', 0),             # F: qty
            data.get('order', ''),          # G: origin_order
            data.get('location', ''),       # H: location
            1,                              # I: status (1-mavjud)
            "",                             # J: image_id
            str(data.get('user_id', '')),   # K: created_by_user_id
            data.get('user_name', ''),      # L: created_by_name
            hozirgi_vaqt,                   # M: created_at
            "",                             # N: used_by_user_id
            "",                             # O: used_by_name
            "",                             # P: used_for_order
            ""                              # Q: used_at
        ]
        
        sheet.append_row(row, value_input_option='USER_ENTERED')
        print(f"✅ Sheetga to'g'ri tartibda qo'shildi: #{new_id}")
    except Exception as e: 
        print(f"❌ Sheetga yozishda xato: {e}")
        

def mark_as_used_in_sheet(r_id, user_id, user_name, order_for):
    """Qoldiq ishlatilganda Sheetdagi N-Q ustunlarini to'ldiradi"""
    client = get_sheet_client()
    if not client: return
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
        # ID ustunidan (A) kerakli qatorni qidiramiz
        cell = sheet.find(f"#{r_id}")
        if cell:
            row_num = cell.row
            hozir = datetime.now().strftime("%d.%m.%Y %H:%M")
            
            # I: Statusni 0 (Ishlatilgan) qilish
            sheet.update_cell(row_num, 9, 0) 
            
            # N, O, P, Q ustunlarini yangilash
            updates = [
                {'range': f'N{row_num}:Q{row_num}', 'values': [[str(user_id), user_name, order_for, hozir]]}
            ]
            sheet.batch_update(updates)
            print(f"✅ Sheetda #{r_id} ishlatildi deb belgilandi.")
    except Exception as e:
        print(f"❌ Sheetni yangilashda xato (used): {e}")
        

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
